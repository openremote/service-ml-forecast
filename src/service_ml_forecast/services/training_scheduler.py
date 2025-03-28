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
import threading

from service_ml_forecast.models.ml_config import MLConfig
from service_ml_forecast.services.ml_config_storage_service import MLConfigStorageService
from service_ml_forecast.util.singleton import Singleton

logger = logging.getLogger(__name__)


class TrainingScheduler(Singleton):
    """
    Manages the scheduling of training jobs for available Model configurations.
    """

    def __init__(self) -> None:
        self.ml_config_storage_service = MLConfigStorageService()
        self.configs: list[MLConfig] = self.ml_config_storage_service.get_all_configs() or []
        self.scheduler_thread: threading.Thread | None = None
        self.running: bool = False
        self.__start()

    def __start(self) -> None:
        if self.scheduler_thread is None or not self.scheduler_thread.is_alive():
            self.running = True
            self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
            self.scheduler_thread.start()
            logger.info("Scheduler has been started")

    def stop(self) -> None:
        self.running = False
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=5.0)
            logger.info("Scheduler has been stopped")

    def _run_scheduler(self) -> None:
        stop_event = threading.Event()

        while self.running:
            self._schedule_training()

            stop_event.wait(timeout=1)

    def _schedule_training(self) -> None:
        pass
