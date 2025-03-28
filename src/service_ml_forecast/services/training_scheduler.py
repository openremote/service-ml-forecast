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

from apscheduler.executors.pool import ProcessPoolExecutor
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.schedulers.background import BackgroundScheduler

from service_ml_forecast.clients.openremote.openremote_client import OpenRemoteClient
from service_ml_forecast.config import env
from service_ml_forecast.ml.ml_provider_factory import MLProviderFactory
from service_ml_forecast.models.ml_config import MLConfig
from service_ml_forecast.models.ml_data_models import FeatureDatapoints, TrainingFeatureSet
from service_ml_forecast.services.ml_config_storage_service import MLConfigStorageService
from service_ml_forecast.util.singleton import Singleton
from service_ml_forecast.util.time_util import TimeUtil

logger = logging.getLogger(__name__)


class TrainingScheduler(Singleton):
    """
    Manages the scheduling of training jobs for available Model configurations.
    """

    def __init__(self) -> None:
        self.config_storage = MLConfigStorageService()
        self.configs: list[MLConfig] = self.config_storage.get_all_configs() or []
        self.misfire_grace_time = 60 * 60

        # Scheduler configuration

        max_instances = 1
        coalesce = True
        executors = {"default": ProcessPoolExecutor(max_workers=1)}
        jobstores = {"default": MemoryJobStore()}

        # Set up the scheduler
        self.scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            daemon=True,
            coalesce=coalesce,
            max_instances=max_instances,
        )

    def start(self) -> None:
        """Start the training scheduler and schedule all the jobs."""

        if self.scheduler.running:
            logger.warning("Scheduler for ML Model Training already running")
            return
        try:
            self.scheduler.start()

            for config in self.configs:
                try:
                    # Schedule the job to train the model
                    seconds = TimeUtil.parse_iso_duration(config.training_interval)

                    self.scheduler.add_job(
                        _execute_ml_training,
                        trigger="interval",
                        args=[config],
                        seconds=seconds,
                        name=f"model-training-{config.id}",
                        misfire_grace_time=self.misfire_grace_time,
                    )

                except Exception as e:
                    logger.error(f"Failed to schedule training job for {config.id}: {e}")

        except Exception as e:
            logger.error(f"Failed to start training scheduler: {e}")
            raise e

    def stop(self) -> None:
        """Stop the training scheduler."""
        self.scheduler.shutdown()


def _execute_ml_training(config: MLConfig) -> None:
    """Train the model for the given configuration."""

    start_time = time.perf_counter()
    logger.info(f"Training job for {config.id} started")

    ml_provider = MLProviderFactory.create_provider(config)

    openremote_client = OpenRemoteClient(
        openremote_url=env.OPENREMOTE_URL,
        keycloak_url=env.OPENREMOTE_KEYCLOAK_URL,
        service_user=env.OPENREMOTE_SERVICE_USER,
        service_user_secret=env.OPENREMOTE_SERVICE_USER_SECRET,
    )

    # Retrieve the target feature datapoints
    target_feature_datapoints: FeatureDatapoints

    try:
        target_feature_datapoints = FeatureDatapoints(
            attribute_name=config.target.attribute_name,
            datapoints=openremote_client.retrieve_historical_datapoints(
                config.target.asset_id,
                config.target.attribute_name,
                config.target.cutoff_timestamp,
                TimeUtil.get_timestamp_ms(),
            ),
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
