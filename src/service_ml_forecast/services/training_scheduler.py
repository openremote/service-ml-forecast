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
from datetime import timedelta

from apscheduler.executors.pool import ProcessPoolExecutor, ThreadPoolExecutor
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.schedulers.background import BackgroundScheduler

from service_ml_forecast.clients.openremote.openremote_client import OpenRemoteClient
from service_ml_forecast.config import ENV
from service_ml_forecast.ml.ml_provider_factory import MLProviderFactory
from service_ml_forecast.models.ml_config import MLConfig
from service_ml_forecast.models.ml_data_models import FeatureDatapoints, TrainingFeatureSet
from service_ml_forecast.services.ml_config_storage_service import MLConfigStorageService
from service_ml_forecast.util.singleton import Singleton
from service_ml_forecast.util.time_util import TimeUtil

logger = logging.getLogger(__name__)


# Standalone function for training that can be pickled and sent to a process
def _execute_ml_training(config: MLConfig) -> None:
    """Train the model for the given configuration."""

    start_time = time.perf_counter()
    logger.info(f"Training job for {config.id} started")

    ml_provider = MLProviderFactory.create_provider(config)

    # Todo use DI for the client, so we can swap client implementations
    openremote_client = OpenRemoteClient(
        openremote_url=ENV.OPENREMOTE_URL,
        keycloak_url=ENV.OPENREMOTE_KEYCLOAK_URL,
        service_user=ENV.OPENREMOTE_SERVICE_USER,
        service_user_secret=ENV.OPENREMOTE_SERVICE_USER_SECRET,
    )

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

    # Train the model
    model = ml_provider.train_model(training_feature_set)

    # Save the model
    ml_provider.save_model(model)

    end_time = time.perf_counter()
    logger.info(f"Training job for {config.id} completed - duration: {end_time - start_time}s")


class TrainingScheduler(Singleton):
    """
    Manages the scheduling of training jobs for available Model configurations.
    """

    def __init__(self) -> None:
        self.config_storage = MLConfigStorageService()
        self.job_misfire_grace_time = 60  # grace period of 1 minute
        self.config_refresh_interval = 30  # 30 seconds

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
            job_defaults={"misfire_grace_time": self.job_misfire_grace_time},
        )

    def start(self) -> None:
        """Start the training scheduler and schedule all the jobs."""

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
                name="training:config-refresh",
                executor="thread_pool",
            )

        except Exception as e:
            logger.error(f"Failed to start training scheduler: {e}")
            raise e

    def stop(self) -> None:
        """Stop the training scheduler."""
        self.scheduler.shutdown()

    def _add_training_job(self, config: MLConfig) -> None:
        job_id = f"training:model-training-{config.id}"
        seconds = TimeUtil.parse_iso_duration(config.training_interval)

        # skip training job if interval is the same
        if self._has_same_interval(job_id, seconds):
            return

        self.scheduler.add_job(
            _execute_ml_training,
            trigger="interval",
            args=[config],
            seconds=seconds,
            id=job_id,
            name=job_id,
            executor="process_pool",
        )

    def _refresh_configs(self) -> None:
        try:
            configs = self.config_storage.get_all_configs()
            if not configs:
                return

            for config in configs:
                self._add_training_job(config)

        except Exception as e:
            logger.error(f"Failed to refresh configurations: {e}")

    def _has_same_interval(self, job_id: str, seconds: int) -> bool:
        existing_job = self.scheduler.get_job(job_id)
        if existing_job is not None and existing_job.trigger.interval is not None:
            existing_job_interval: timedelta = existing_job.trigger.interval
            return existing_job_interval.total_seconds() == seconds
        return False
