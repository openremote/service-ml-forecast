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

from apscheduler.executors.pool import ProcessPoolExecutor
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.schedulers.background import BackgroundScheduler

from service_ml_forecast.ml.ml_provider_factory import MLProviderFactory
from service_ml_forecast.models.ml_config import MLConfig
from service_ml_forecast.services.ml_config_storage_service import MLConfigStorageService
from service_ml_forecast.util.singleton import Singleton

logger = logging.getLogger(__name__)


class TrainingScheduler(Singleton):
    """
    Manages the scheduling of training jobs for available Model configurations.
    """

    def __init__(self) -> None:
        self.config_storage = MLConfigStorageService()
        self.configs: list[MLConfig] = self.config_storage.get_all_configs() or []

        # Scheduler configuration
        misfire_grace_time = 3600
        executors = {"default": ProcessPoolExecutor(max_workers=1)}
        jobstores = {"default": MemoryJobStore()}

        # Setup the scheduler
        self.scheduler = BackgroundScheduler(
            jobstores=jobstores, executors=executors, misfire_grace_time=misfire_grace_time
        )

    def start(self) -> None:
        """Start the training scheduler and schedule all the jobs."""

        if self.scheduler.running:
            logger.warning("Scheduler for ML Model Training already running")
            return

        try:
            self.scheduler.start()
            self.schedule_jobs()
        except Exception as e:
            logger.error(f"Failed to start training scheduler: {e}")
            raise e

    def schedule_jobs(self) -> None:
        """Schedule all the jobs for the available Model configurations."""
        for config in self.configs:
            try:
                _ml_provider = MLProviderFactory.create_provider(config)
                logger.info(f"Scheduling training job for {config.id}")

            except Exception as e:
                logger.error(f"Failed to schedule training job for {config.id}: {e}")
