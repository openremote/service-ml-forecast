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

import logging
import time

from apscheduler.executors.pool import ProcessPoolExecutor, ThreadPoolExecutor
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.schedulers.background import BackgroundScheduler

from service_ml_forecast.common.singleton import Singleton
from service_ml_forecast.common.time_util import TimeUtil
from service_ml_forecast.ml.model_provider_factory import ModelProviderFactory
from service_ml_forecast.models.model_config import ModelConfig
from service_ml_forecast.services.model_config_service import ModelConfigService
from service_ml_forecast.services.openremote_service import OpenRemoteService

logger = logging.getLogger(__name__)

CONFIG_WATCHER_JOB_ID = "model:config-watcher"
TRAINING_JOB_ID_PREFIX = "model:training"
FORECAST_JOB_ID_PREFIX = "model:forecast"

JOB_GRACE_PERIOD = 60  # Allow jobs to be late a maximum of 1 minute, otherwise reschedule

CONFIG_POLLING_INTERVAL = 10  # Poll configs for changes every 10 seconds


class ModelScheduler(Singleton):
    """Manages the scheduling of ML model training and forecasting jobs."""

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
            job_defaults={"misfire_grace_time": JOB_GRACE_PERIOD},
            logger=logger,
        )

    def start(self) -> None:
        """Start the scheduler for ML model training and forecasting.

        Does not start the scheduler if it is already running.
        """
        if self.scheduler.running:
            logger.warning("Scheduler for ML Model Training already running")
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
        seconds = TimeUtil.parse_iso_duration(config.training_interval)

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
    """Model training job. Constructs the model provider, retrieves the training feature set,
    trains the model, and saves the model.

    Args:
        config: The model configuration
        data_service: The data service
    """
    start_time = time.perf_counter()
    provider = ModelProviderFactory.create_provider(config)

    training_feature_set = data_service.get_training_feature_set(config)

    if training_feature_set is None:
        logger.error(
            f"Cannot train model {config.id} - no training feature set found. "
            f"Asset ID: {config.target.asset_id}, Attribute: {config.target.attribute_name}, "
        )
        return

    # Train the model
    model = provider.train_model(training_feature_set)

    if model is None:
        logger.error(
            f"Model training failed for {config.id} - no model returned. "
            f"Type: {config.type}, Training Interval: {config.training_interval}"
        )
        return

    # Save the model
    provider.save_model(model)

    end_time = time.perf_counter()
    logger.info(
        f"Training job for {config.id} completed - duration: {end_time - start_time}s. "
        f"Type: {config.type}, Training Interval: {config.training_interval}"
    )


def _model_forecast_job(config: ModelConfig, data_service: OpenRemoteService) -> None:
    """Model forecast job. Constructs the model provider, retrieves the forecast feature set,
    generates the forecast, and writes the forecasted datapoints to OpenRemote.

    Args:
        config: The model configuration
        data_service: The data service
    """
    start_time = time.perf_counter()
    provider = ModelProviderFactory.create_provider(config)

    # Retrieve the forecast feature set
    forecast_feature_set = data_service.get_forecast_feature_set(config)

    if config.regressors is not None and forecast_feature_set is None:
        logger.error(
            f"Cannot forecast model {config.id} - config has regressors but no forecast feature set. "
            f"Asset ID: {config.target.asset_id}, Attribute: {config.target.attribute_name}, "
            f"Regressors: {', '.join(r.attribute_name for r in config.regressors)}"
        )
        return

    # Generate the forecast
    forecast = provider.generate_forecast(forecast_feature_set)

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

    end_time = time.perf_counter()
    logger.info(
        f"Forecasting job for {config.id} completed - duration: {end_time - start_time}s. "
        f"Wrote {len(forecast.datapoints)} datapoints. "
        f"Asset ID: {config.target.asset_id}, Attribute: {config.target.attribute_name}"
    )
