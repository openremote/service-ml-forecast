# Copyright 2025, OpenRemote Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import datetime
import logging
import math
import time
from typing import Any

import pandas as pd
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED, JobExecutionEvent
from apscheduler.executors.pool import ProcessPoolExecutor, ThreadPoolExecutor
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.schedulers.background import BackgroundScheduler

from service_ml_forecast.common.exceptions import ResourceValidationError
from service_ml_forecast.common.model_lock import model_operation_lock
from service_ml_forecast.common.singleton import Singleton
from service_ml_forecast.common.time_util import TimeUtil
from service_ml_forecast.ml.model_provider_factory import ModelProviderFactory, get_all_covariates
from service_ml_forecast.models.feature_data_wrappers import ForecastResult
from service_ml_forecast.models.model_config import ModelConfig
from service_ml_forecast.models.model_type import ModelTypeEnum
from service_ml_forecast.services.model_config_service import ModelConfigService
from service_ml_forecast.services.model_storage_service import ModelStorageService
from service_ml_forecast.services.openremote_service import OpenRemoteService

logger = logging.getLogger(__name__)

CONFIG_WATCHER_JOB_ID = "model:config-watcher"
TRAINING_JOB_ID_PREFIX = "model:training"
FORECAST_JOB_ID_PREFIX = "model:forecast"
FORECAST_RECOVERY_DELAY_SECONDS = 30
MAX_FORECAST_RECOVERY_ATTEMPTS = 3

CONFIG_POLLING_INTERVAL = 30  # Poll configs for changes every 30 seconds


class ModelScheduler(Singleton):
    """Manages the scheduling of model training and forecasting jobs."""

    def __init__(self, openremote_service: OpenRemoteService) -> None:
        self.config_storage = ModelConfigService(openremote_service)
        self.openremote_service = openremote_service

        executors = {
            "process_pool": ProcessPoolExecutor(max_workers=1),  # For CPU-intensive training tasks
            "thread_pool": ThreadPoolExecutor(max_workers=1),  # For I/O-bound refresh tasks
        }
        jobstores = {"default": MemoryJobStore()}

        self.scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            daemon=True,  # Ensure any threads/processes are properly exited when the main process exits
            coalesce=True,
            max_instances=1,
            job_defaults={"misfire_grace_time": None},  # Allows jobs to run even if their execution is delayed
            logger=logger,
        )
        self._forecast_recovery_attempts: dict[str, int] = {}
        self.scheduler.add_listener(self._on_forecast_job_event, EVENT_JOB_ERROR | EVENT_JOB_EXECUTED)

    def _on_forecast_job_event(self, event: JobExecutionEvent) -> None:
        """Retry transient dependency failures without waiting a full forecast interval.

        Reuse the existing job, arguments and publication checks. Invalid input,
        model and configuration errors retain the normal schedule. Three quick
        retries bound a continuous outage; success resets the recovery budget.
        """
        if not event.job_id.startswith(FORECAST_JOB_ID_PREFIX + ":"):
            return
        if event.exception is None:
            self._forecast_recovery_attempts.pop(event.job_id, None)
            return
        error = event.exception
        transient = isinstance(error, ConnectionError | TimeoutError)
        if not transient:
            return
        job = self.scheduler.get_job(event.job_id)
        if job is None or not job.args or not job.args[0].enabled:
            return
        attempts = self._forecast_recovery_attempts.get(event.job_id, 0)
        if attempts >= MAX_FORECAST_RECOVERY_ATTEMPTS:
            logger.warning("Quick recovery exhausted for %s; retaining its regular schedule", event.job_id)
            return
        self._forecast_recovery_attempts[event.job_id] = attempts + 1
        retry_at = datetime.datetime.now(datetime.UTC) + datetime.timedelta(seconds=FORECAST_RECOVERY_DELAY_SECONDS)
        self.scheduler.modify_job(event.job_id, next_run_time=retry_at)
        logger.info("Retrying %s after a transient dependency failure (attempt %s)", event.job_id, attempts + 1)

    def start(self) -> None:
        """Start the scheduler for model training and forecasting.

        Does not start the scheduler if it is already running.
        """
        if self.scheduler.running:
            logger.warning("Scheduler for Model Training already running")
            return

        self.scheduler.start()
        self._poll_configs()

        self.scheduler.add_job(
            self._poll_configs,
            trigger="interval",
            seconds=CONFIG_POLLING_INTERVAL,
            id=CONFIG_WATCHER_JOB_ID,
            name=CONFIG_WATCHER_JOB_ID,
            executor="thread_pool",
        )

    def stop(self) -> None:
        """Stop the scheduler, does not interrupt any running jobs."""

        self.scheduler.shutdown()

    def _add_training_job(self, config: ModelConfig) -> None:
        """Add a training job for the given model config."""

        job_id = f"{TRAINING_JOB_ID_PREFIX}:{config.id}"
        seconds = TimeUtil.parse_iso_duration(config.forecast_interval)

        if not self._is_job_scheduling_needed(job_id, config):
            return

        self.scheduler.add_job(
            _model_training_job,
            trigger="interval",
            args=[config, self.openremote_service],
            seconds=seconds,
            id=job_id,
            name=job_id,
            executor="process_pool",
            replace_existing=True,
        )
        logger.info("Scheduled training %s every %s seconds", config.id, seconds)

    def _add_forecast_job(self, config: ModelConfig) -> None:
        """Add a forecast job for the given model config."""

        job_id = f"{FORECAST_JOB_ID_PREFIX}:{config.id}"
        seconds = TimeUtil.parse_iso_duration(config.forecast_interval)

        if not self._is_job_scheduling_needed(job_id, config):
            return

        self.scheduler.add_job(
            _model_forecast_job,
            trigger="interval",
            args=[config, self.openremote_service],
            seconds=seconds,
            id=job_id,
            name=job_id,
            executor="process_pool",
            replace_existing=True,
        )
        logger.info("Scheduled forecasts %s every %s seconds", config.id, seconds)

    def _poll_configs(self) -> None:
        """Poll for configurations and schedule the jobs based on the new configs"""

        configs = self.config_storage.get_all()
        self._cleanup_stale_jobs(configs)

        # Queue training and forecast jobs for enabled configs
        for config in configs:
            if config.enabled:
                self._add_training_job(config)
                self._add_forecast_job(config)

    def _cleanup_stale_jobs(self, configs: list[ModelConfig]) -> None:
        """Remove jobs for configs that are no longer present in the config storage"""

        # training and forecast jobs for the given configs that are enabled
        training_jobs = [f"{TRAINING_JOB_ID_PREFIX}:{config.id}" for config in configs if config.enabled]
        forecast_jobs = [f"{FORECAST_JOB_ID_PREFIX}:{config.id}" for config in configs if config.enabled]

        expected_jobs = training_jobs + forecast_jobs + [CONFIG_WATCHER_JOB_ID]

        for job in self.scheduler.get_jobs():
            if job.id not in expected_jobs:
                self.scheduler.remove_job(job.id)
        if hasattr(self, "_forecast_recovery_attempts"):
            self._forecast_recovery_attempts = {
                key: value for key, value in self._forecast_recovery_attempts.items() if key in forecast_jobs
            }

    def _is_job_scheduling_needed(self, job_id: str, config: ModelConfig) -> bool:
        """Compares the given config with the config of an existing job.

        Returns True if the job is not scheduled or if the config has changed.
        """
        existing_job = self.scheduler.get_job(job_id)

        # If the job is not scheduled, then scheduling is needed
        if existing_job is None or existing_job.args is None:
            return True

        # Reschedule if the config has changed
        job_config: ModelConfig = existing_job.args[0]
        return job_config != config


def _model_training_job(config: ModelConfig, data_service: OpenRemoteService) -> None:
    with model_operation_lock(config.id, "training"):
        _run_model_training_job(config, data_service)


def _run_model_training_job(config: ModelConfig, data_service: OpenRemoteService) -> None:
    """Model training job. Constructs the model provider, retrieves the training feature set,
    trains the model, and saves the model.

    Args:
        config: The model configuration
        data_service: The data service
    """
    start_time = time.perf_counter()
    current = ModelConfigService(data_service).get(config.realm, config.id)
    storage = ModelStorageService()
    if not current.enabled or storage.fingerprint(current) != storage.fingerprint(config):
        raise ResourceValidationError(f"Training job has a stale config: {config.id}")
    storage.mark_training_pending(config)
    provider = ModelProviderFactory.create_provider(config)

    training_dataset = data_service.get_training_dataset(config)

    if training_dataset is None:
        logger.error(
            f"Cannot train model {config.id} - no training dataset found. "
            f"Asset ID: {config.target.asset_id}, Attribute: {config.target.attribute_name}, "
        )
        return

    # Train the model
    model = provider.train_model(training_dataset)

    if model is None:
        logger.error(
            f"Model training failed for {config.id} - no model returned. "
            f"Type: {config.type}, Training Interval: {config.forecast_interval}"
        )
        return

    # Save the model
    current = ModelConfigService(data_service).get(config.realm, config.id)
    if not current.enabled or storage.fingerprint(current) != storage.fingerprint(config):
        raise ResourceValidationError(f"Config changed during training: {config.id}")
    provider.save_model(model)

    # Log the first and last datapoint datetimes of the target attribute
    target_first_datapoint_datetime = datetime.datetime.fromtimestamp(training_dataset.target.datapoints[0].x / 1000)
    target_last_datapoint_datetime = datetime.datetime.fromtimestamp(training_dataset.target.datapoints[-1].x / 1000)

    end_time = time.perf_counter()
    logger.info(
        f"Training job for {config.id} completed - duration: {end_time - start_time}s, "
        f"Type: {config.type}, Training Interval: {config.forecast_interval}, "
        f"Target first datapoint datetime: {target_first_datapoint_datetime}, "
        f"Target last datapoint datetime: {target_last_datapoint_datetime}"
    )


def _model_forecast_job(config: ModelConfig, data_service: OpenRemoteService) -> None:
    with model_operation_lock(config.id, "forecast"):
        with ModelStorageService().pin_forecast(config) as manifest:
            _run_model_forecast_job(config, data_service, manifest)


def _run_model_forecast_job(
    config: ModelConfig, data_service: OpenRemoteService, generating_manifest: dict[str, Any]
) -> None:
    """Model forecast job. Constructs the model provider, retrieves the forecast dataset,
    generates the forecast, and writes the forecasted datapoints to OpenRemote.

    Args:
        config: The model configuration
        data_service: The data service
    """
    start_time = time.perf_counter()
    current = ModelConfigService(data_service).get(config.realm, config.id)
    storage = ModelStorageService()
    if not current.enabled or storage.fingerprint(current) != storage.fingerprint(config):
        raise ResourceValidationError(f"Forecast job has a stale or disabled config: {config.id}")
    storage.get_ready_manifest(config)
    provider = ModelProviderFactory.create_provider(config)

    # Retrieve the forecast dataset
    forecast_dataset = data_service.get_forecast_dataset(config)

    all_covariates = get_all_covariates(config)
    if len(all_covariates) > 0 and forecast_dataset is None:
        logger.error(
            f"Cannot forecast model {config.id} - config has covariates but no forecast dataset. "
            f"Asset ID: {config.target.asset_id}, Attribute: {config.target.attribute_name}, "
            f"Covariates: {', '.join(r.attribute_name for r in all_covariates)}"
        )
        return

    # Generate the forecast
    forecast = provider.generate_forecast(forecast_dataset)

    # A config may have changed while prediction was running. Never publish
    # results from an old job after a model switch or parameter update.
    current = ModelConfigService(data_service).get(config.realm, config.id)
    if not current.enabled or storage.fingerprint(current) != storage.fingerprint(config):
        raise ResourceValidationError(f"Config changed during forecast: {config.id}")
    manifest = storage.get_ready_manifest(config)
    if manifest["revision"] != generating_manifest["revision"]:
        raise ResourceValidationError(f"Model revision changed during forecast: {config.id}")
    _validate_forecast_before_write(config, forecast, manifest.get("training_cutoff"))

    # Write the forecasted datapoints
    if not data_service.write_predicted_datapoints(
        config,
        forecast.datapoints,
    ):
        logger.error(
            f"Failed to write forecasted datapoints for {config.id}. "
            f"Asset ID: {config.target.asset_id}, Attribute: {config.target.attribute_name}, "
            f"Forecast Size: {len(forecast.datapoints)}, "
        )
        return

    storage.record_forecast(
        config,
        forecast.datapoints[0].x,
        forecast.datapoints[-1].x,
        len(forecast.datapoints),
        manifest=generating_manifest,
    )

    end_time = time.perf_counter()

    # Log the first and last datapoint datetimes of the forecast
    first_datapoint_datetime = datetime.datetime.fromtimestamp(forecast.datapoints[0].x / 1000)
    last_datapoint_datetime = datetime.datetime.fromtimestamp(forecast.datapoints[-1].x / 1000)

    logger.info(
        f"Forecasting job for {config.id} completed - duration: {end_time - start_time}s, "
        f"Wrote {len(forecast.datapoints)} datapoints, "
        f"First datapoint datetime: {first_datapoint_datetime}, Last datapoint datetime: {last_datapoint_datetime}, "
        f"Asset ID: {config.target.asset_id}, Attribute: {config.target.attribute_name}"
    )


def _validate_forecast_before_write(config: ModelConfig, forecast: ForecastResult, training_cutoff: str | None) -> None:
    """Reject stale, misrouted, incomplete, or invalid predictions."""
    points = forecast.datapoints
    if forecast.asset_id != config.target.asset_id or forecast.attribute_name != config.target.attribute_name:
        raise ResourceValidationError(f"Forecast target does not match config: {config.id}")
    if len(points) != config.forecast_periods:
        raise ResourceValidationError(f"Forecast has the wrong number of periods: {config.id}")
    if points[0].x <= TimeUtil.get_timestamp_ms():
        raise ResourceValidationError(f"Forecast starts in the past: {config.id}")
    try:
        if not isinstance(training_cutoff, str):
            raise ValueError("Missing training cutoff")
        cutoff = pd.Timestamp(training_cutoff)
        if pd.isna(cutoff):
            raise ValueError("Missing training cutoff")
        if cutoff.tzinfo is not None:
            cutoff = cutoff.tz_convert("UTC").tz_localize(None)
        frequency = pd.tseries.frequencies.to_offset(config.forecast_frequency)
        # WEA retains raw minute timestamps and anchors its issue to a UTC bin.
        # Darts stores the end of its already-resampled training series.
        if config.type == ModelTypeEnum.WEA:
            cutoff = cutoff.floor(config.forecast_frequency)
        expected_first = cutoff + frequency
        if points[0].x != expected_first.value // 1_000_000:
            raise ValueError("Forecast start differs from the trained horizon")
    except (ValueError, TypeError, OverflowError) as error:
        raise ResourceValidationError(f"Forecast does not match its training cutoff: {config.id}") from error
    expected = pd.date_range(
        start=pd.Timestamp(points[0].x, unit="ms"),
        periods=config.forecast_periods,
        freq=config.forecast_frequency,
    )
    actual = pd.to_datetime([point.x for point in points], unit="ms")
    if not expected.equals(actual):
        raise ResourceValidationError(f"Forecast timestamps are not contiguous: {config.id}")
    if any(point.y is None or not math.isfinite(float(point.y)) for point in points):
        raise ResourceValidationError(f"Forecast contains non-finite values: {config.id}")
