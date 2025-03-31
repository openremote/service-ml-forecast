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
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
import time

from apscheduler.executors.pool import ProcessPoolExecutor, ThreadPoolExecutor
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.schedulers.background import BackgroundScheduler

from service_ml_forecast.clients.openremote.openremote_client import OpenRemoteClient
from service_ml_forecast.ml.ml_model_provider_factory import MLModelProviderFactory
from service_ml_forecast.models.ml_data_wrappers import FeatureDatapoints, TrainingFeatureSet
from service_ml_forecast.models.ml_model_config import MLModelConfig
from service_ml_forecast.services.ml_model_config_service import MLModelConfigService
from service_ml_forecast.util.singleton import Singleton
from service_ml_forecast.util.time_util import TimeUtil

logger = logging.getLogger(__name__)

CONFIG_WATCHER_JOB_ID = "ml:config-watcher"
TRAINING_JOB_ID_PREFIX = "ml:training"
FORECAST_JOB_ID_PREFIX = "ml:forecast"

JOB_GRACE_PERIOD = 60  # 1 minute (time to run the job after the scheduled time)

CONFIG_REFRESH_INTERVAL = 30  # 30 seconds


class MLModelScheduler(Singleton):
    """
    Manages the scheduling of ML model training and forecasting jobs.
    """

    def __init__(self, openremote_client: OpenRemoteClient) -> None:
        self.config_storage = MLModelConfigService()
        self.openremote_client = openremote_client

        executors = {
            "process_pool": ProcessPoolExecutor(max_workers=1),  # For CPU-intensive training tasks
            "thread_pool": ThreadPoolExecutor(max_workers=1),  # For I/O-bound refresh tasks
        }
        jobstores = {"default": MemoryJobStore()}

        self.scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            daemon=True,
            coalesce=True,
            max_instances=1,
            job_defaults={"misfire_grace_time": JOB_GRACE_PERIOD},
        )

    def start(self) -> None:
        """Start the scheduler for ML model training and forecasting.

        If the scheduler is already running, it will not be started again.
        """

        if self.scheduler.running:
            logger.warning("Scheduler for ML Model Training already running")
            return
        try:
            self.scheduler.start()
            self._poll_configs()

            # Schedule the configuration watcher
            self.scheduler.add_job(
                self._poll_configs,
                trigger="interval",
                seconds=CONFIG_REFRESH_INTERVAL,
                id=CONFIG_WATCHER_JOB_ID,
                name=CONFIG_WATCHER_JOB_ID,
                executor="thread_pool",
            )

        except Exception as e:
            logger.critical(f"Failed to start ML Model Scheduler: {e}")
            raise e

    def stop(self) -> None:
        """Stop the scheduler"""
        self.scheduler.shutdown()

    def _add_training_job(self, config: MLModelConfig) -> None:
        job_id = f"{TRAINING_JOB_ID_PREFIX}:{config.id}"
        seconds = TimeUtil.parse_iso_duration(config.training_interval)

        # Do not add the job if the config has not changed
        if self._has_no_config_changes(job_id, config):
            return

        self.scheduler.add_job(
            _execute_ml_training,
            trigger="interval",
            args=[config, self.openremote_client],
            seconds=seconds,
            id=job_id,
            name=job_id,
            executor="process_pool",
            replace_existing=True,
        )

    def _add_forecast_job(self, config: MLModelConfig) -> None:
        job_id = f"{FORECAST_JOB_ID_PREFIX}:{config.id}"
        seconds = TimeUtil.parse_iso_duration(config.forecast_interval)

        # Do not add the job if the config has not changed
        if self._has_no_config_changes(job_id, config):
            return

        self.scheduler.add_job(
            _execute_ml_forecast,
            trigger="interval",
            args=[config, self.openremote_client],
            seconds=seconds,
            id=job_id,
            name=job_id,
            executor="process_pool",
            replace_existing=True,
        )

    def _poll_configs(self) -> None:
        """Poll for configurations and schedule the jobs based on the new configs"""
        try:
            configs = self.config_storage.get_all()
            if not configs:
                return

            for config in configs:
                # Order is important here (train -> forecast)
                self._add_training_job(config)
                self._add_forecast_job(config)
        except Exception as e:
            logger.error(f"Failed to poll configurations and schedule jobs: {e}")

    def _has_no_config_changes(self, job_id: str, config: MLModelConfig) -> bool:
        existing_job = self.scheduler.get_job(job_id)

        if existing_job is not None and existing_job.args is not None:
            job_config: MLModelConfig = existing_job.args[0]
            return job_config == config

        return False


def _execute_ml_training(config: MLModelConfig, openremote_client: OpenRemoteClient) -> None:
    """Standalone function for ML model training (can be sent to a process)

    Args:
        config: The configuration to use for training
        openremote_client: The OpenRemote client to retrieve datapoints from
    """
    start_time = time.perf_counter()
    provider = MLModelProviderFactory.create_provider(config)

    target_feature_datapoints: FeatureDatapoints

    # Retrieve target feature datapoints from OpenRemote
    datapoints = openremote_client.retrieve_historical_datapoints(
        config.target.asset_id,
        config.target.attribute_name,
        config.target.cutoff_timestamp,
        TimeUtil.get_timestamp_ms(),
    )

    if datapoints is None:
        logger.error(f"Training failed, could not retrieve target feature datapoints for {config.id}")
        return

    target_feature_datapoints = FeatureDatapoints(
        attribute_name=config.target.attribute_name,
        datapoints=datapoints,
    )

    regressors: list[FeatureDatapoints] = []

    if config.regressors is not None:
        for regressor in config.regressors:
            # Retrieve regressor feature datapoints from OpenRemote
            regressor_datapoints = openremote_client.retrieve_historical_datapoints(
                regressor.asset_id,
                regressor.attribute_name,
                regressor.cutoff_timestamp,
                TimeUtil.get_timestamp_ms(),
            )

            if regressor_datapoints is None:
                logger.error(
                    f"Training failed, could not retrieve regressor datapoints for {config.id}"
                    f" - {regressor.asset_id} - {regressor.attribute_name}"
                )
                return

            regressors.append(
                FeatureDatapoints(
                    attribute_name=regressor.attribute_name,
                    datapoints=regressor_datapoints,
                )
            )

    training_feature_set = TrainingFeatureSet(
        target=target_feature_datapoints,
        regressors=regressors if regressors else None,
    )

    # Train the model
    model = provider.train_model(training_feature_set)

    if model is None:
        logger.error(f"Training failed, did not receive serialized model for {config.id}")
        return

    if not provider.save_model(model):
        logger.error(f"Training failed, could not save model for {config.id}")
        return

    end_time = time.perf_counter()
    logger.info(f"Training job for {config.id} completed - duration: {end_time - start_time}s")


def _execute_ml_forecast(config: MLModelConfig, openremote_client: OpenRemoteClient) -> None:
    """Standalone function for ML model forecasting (can be sent to a process)

    Args:
        config: The configuration to use for forecasting
        openremote_client: The OpenRemote client to retrieve datapoints from
    """

    start_time = time.perf_counter()
    provider = MLModelProviderFactory.create_provider(config)

    # TODO: Handle regressors (we need provide multi-regressor models with the forecasted datapoints for each regressor)

    # Generate the forecast
    forecast = provider.generate_forecast()

    if forecast is None:
        logger.error(f"Forecasting failed, could not generate forecast for {config.id}")
        return

    # Write the forecasted datapoints to OpenRemote
    datapoints_written = openremote_client.write_predicted_datapoints(
        config.target.asset_id,
        config.target.attribute_name,
        forecast.datapoints,
    )
    if not datapoints_written:
        logger.error(f"Forecasting failed, could not write forecast for {config.id}")
        return

    end_time = time.perf_counter()
    logger.info(
        f"Forecasting job for {config.id} completed - duration: {end_time - start_time}s"
        f" - wrote {len(forecast.datapoints)} datapoints"
    )
