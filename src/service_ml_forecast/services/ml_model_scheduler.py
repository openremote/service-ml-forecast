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

CONFIG_REFRESH_JOB_ID = "ml:config-refresh"
TRAINING_JOB_ID_PREFIX = "ml:training"
FORECASTING_JOB_ID_PREFIX = "ml:forecasting"

JOB_GRACE_PERIOD = 60  # 1 minute (time to run the job after the scheduled time)


class MLModelScheduler(Singleton):
    """
    Manages the scheduling of ML model training and forecasting jobs.
    """

    def __init__(self, openremote_client: OpenRemoteClient) -> None:
        self.config_storage = MLModelConfigService()
        self.config_refresh_interval = 30  # 30 seconds
        self.openremote_client = openremote_client

        executors = {
            "process_pool": ProcessPoolExecutor(max_workers=1),  # For CPU-intensive training tasks
            "thread_pool": ThreadPoolExecutor(max_workers=1),  # For I/O-bound refresh tasks
        }
        jobstores = {"default": MemoryJobStore()}

        # Set up the scheduler
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

            # Initial configuration load
            self._refresh_configs()

            self.scheduler.add_job(
                self._refresh_configs,
                trigger="interval",
                seconds=self.config_refresh_interval,
                id=CONFIG_REFRESH_JOB_ID,
                name=CONFIG_REFRESH_JOB_ID,
                executor="thread_pool",
            )

        except Exception as e:
            logger.error(f"Failed to start training scheduler: {e}")
            raise e

    def stop(self) -> None:
        """Stop the scheduler"""
        self.scheduler.shutdown()

    def _add_training_job(self, config: MLModelConfig) -> None:
        job_id = f"{TRAINING_JOB_ID_PREFIX}:{config.id}"
        seconds = TimeUtil.parse_iso_duration(config.training_interval)

        # skip if config has not changed
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
        )

    def _refresh_configs(self) -> None:
        """Refresh the configurations and schedule the jobs based on the new configs"""
        try:
            configs = self.config_storage.get_all()
            if not configs:
                return

            for config in configs:
                self._add_training_job(config)

        except Exception as e:
            logger.error(f"Failed to refresh configurations: {e}")

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

    # Retrieve the target feature datapoints
    target_feature_datapoints: FeatureDatapoints

    try:
        datapoints = openremote_client.retrieve_historical_datapoints(
            config.target.asset_id,
            config.target.attribute_name,
            config.target.cutoff_timestamp,
            TimeUtil.get_timestamp_ms(),
        )
        if datapoints is None:
            logger.error(f"Failed to retrieve target feature datapoints for {config.id}")
            return

        target_feature_datapoints = FeatureDatapoints(
            attribute_name=config.target.attribute_name,
            datapoints=datapoints,
        )
    except Exception as e:
        logger.error(f"Failed to retrieve target feature datapoints for {config.id}: {e}")
        return

    # Create the training feature set
    training_feature_set = TrainingFeatureSet(
        target=target_feature_datapoints,
    )

    # TODO: Handle regressors

    # Train the model
    model = provider.train_model(training_feature_set)

    # Save the model
    provider.save_model(model)

    end_time = time.perf_counter()
    logger.info(f"Training job for {config.id} completed - duration: {end_time - start_time}s")


def _execute_ml_forecasting(config: MLModelConfig, openremote_client: OpenRemoteClient) -> None:
    """Standalone function for ML model forecasting (can be sent to a process)

    Args:
        config: The configuration to use for forecasting
        openremote_client: The OpenRemote client to retrieve datapoints from
    """
    pass
