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

from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.schedulers.background import BackgroundScheduler

from openremote_client.models import ServiceInfo
from openremote_client.rest_client import OpenRemoteClient

logger = logging.getLogger(__name__)

HEARTBEAT_JOB_ID = "service:heartbeat"
JOB_GRACE_PERIOD = 60
HEARTBEAT_INTERVAL = 30


class OpenRemoteServiceRegistrar:
    """Manages the registration and heartbeat scheduling for OpenRemote services."""

    def __init__(
        self,
        client: OpenRemoteClient,
        service_info: ServiceInfo,
    ):
        self.client = client
        self.service_info = service_info
        self.instance_id: str | None = None
        self.registered = False
        self._stopped = False

        executors = {
            "thread_pool": ThreadPoolExecutor(max_workers=1),
        }
        jobstores = {"default": MemoryJobStore()}

        self.scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            daemon=True,
            coalesce=True,
            max_instances=1,
            job_defaults={"misfire_grace_time": JOB_GRACE_PERIOD},
            logger=logger,
        )

    def start(self) -> None:
        """Start the scheduler and register the service."""
        if self.scheduler.running:
            logger.warning("Service scheduler already running")
            return

        self.scheduler.start()
        logger.info("Service registrar scheduler started")
        self._register_service()

        self.scheduler.add_job(
            self._send_heartbeat,
            trigger="interval",
            seconds=HEARTBEAT_INTERVAL,
            id=HEARTBEAT_JOB_ID,
            name=HEARTBEAT_JOB_ID,
            executor="thread_pool",
        )

    def stop(self) -> None:
        """Stop the scheduler and deregister the service."""
        if self._stopped:
            return
        self._stopped = True

        if self.registered and self.instance_id:
            self._deregister_service()

        if self.scheduler.running:
            self.scheduler.shutdown()

    def _register_service(self) -> None:
        """Register the service with OpenRemote."""
        try:
            response = self.client.services.register(self.service_info)

            if response is not None:
                self.instance_id = response.instanceId
                self.registered = True
                logger.info(f"Successfully registered service with instance ID: {self.instance_id}")
            else:
                logger.error("Failed to register service with OpenRemote")

        except Exception as e:
            logger.error(f"Error registering service: {e}")

    def _send_heartbeat(self) -> None:
        """Send a heartbeat to OpenRemote."""
        if not self.registered or not self.instance_id:
            logger.warning("Cannot send heartbeat - service not registered, attempting re-registration")
            self._register_service()
            return

        try:
            success = self.client.services.heartbeat(self.service_info.serviceId, self.instance_id)

            if success:
                logger.debug(f"Heartbeat sent successfully for instance: {self.instance_id}")
            else:
                logger.error(f"Failed to send heartbeat for instance: {self.instance_id}, trying re-registration")
                self._register_service()

        except Exception as e:
            logger.error(f"Error sending heartbeat: {e}")

    def _deregister_service(self) -> None:
        """Deregister the service from OpenRemote."""
        if not self.instance_id:
            return

        try:
            success = self.client.services.deregister(self.service_info.serviceId, self.instance_id)

            if success:
                logger.info(f"Successfully deregistered service with instance ID: {self.instance_id}")
                self.registered = False
                self.instance_id = None
            else:
                logger.error(f"Failed to deregister service with instance ID: {self.instance_id}")

        except Exception as e:
            logger.error(f"Error deregistering service: {e}")
