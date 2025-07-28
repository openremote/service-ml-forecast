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


from unittest.mock import Mock

from openremote_client.models import ServiceInfo, ServiceStatus
from openremote_client.service_registrar import OpenRemoteServiceRegistrar


def test_service_registrar_start() -> None:
    """Test that OpenRemoteServiceRegistrar starts correctly."""
    mock_client = Mock()

    # mock response with the instanceId set to the test-instance-id
    mock_response = ServiceInfo(
        serviceId="test-service",
        instanceId="test-instance-id",
        label="Test Service",
        homepageUrl="http://localhost:8000/ui",
        status=ServiceStatus.AVAILABLE,
    )
    mock_client.services.register.return_value = mock_response

    registrar = OpenRemoteServiceRegistrar(
        client=mock_client,
        service_info=ServiceInfo(
            serviceId="test-service",
            label="Test Service",
            homepageUrl="http://localhost:8000/ui",
            status=ServiceStatus.AVAILABLE,
        ),
    )

    registrar.start()

    assert registrar.registered is True
    assert registrar.instance_id == "test-instance-id"
    assert registrar.scheduler.running is True


def test_service_registrar_stop() -> None:
    """Test that OpenRemoteServiceRegistrar stops correctly."""
    mock_client = Mock()
    mock_client.services.deregister.return_value = True

    registrar = OpenRemoteServiceRegistrar(
        client=mock_client,
        service_info=ServiceInfo(
            serviceId="test-service",
            label="Test Service",
            homepageUrl="http://localhost:8000/ui",
            status=ServiceStatus.AVAILABLE,
        ),
    )
    registrar.instance_id = "test-instance-id"
    registrar.registered = True

    # Start the scheduler first so we can stop it
    registrar.scheduler.start()

    registrar.stop()

    assert registrar.registered is False
    assert registrar.instance_id is None


def test_service_registrar_heartbeat() -> None:
    """Test that heartbeat is sent correctly."""
    mock_client = Mock()
    mock_client.services.heartbeat.return_value = True

    registrar = OpenRemoteServiceRegistrar(
        client=mock_client,
        service_info=ServiceInfo(
            serviceId="test-service",
            label="Test Service",
            homepageUrl="http://localhost:8000/ui",
            status=ServiceStatus.AVAILABLE,
        ),
    )
    registrar.instance_id = "test-instance-id"
    registrar.registered = True

    registrar._send_heartbeat()

    mock_client.services.heartbeat.assert_called_once_with("test-service", "test-instance-id")


def test_service_registrar_heartbeat_not_registered() -> None:
    """Test that heartbeat is not sent when service is not registered."""
    mock_client = Mock()

    registrar = OpenRemoteServiceRegistrar(
        client=mock_client,
        service_info=ServiceInfo(
            serviceId="test-service",
            label="Test Service",
            homepageUrl="http://localhost:8000/ui",
            status=ServiceStatus.AVAILABLE,
        ),
    )
    registrar.registered = False

    registrar._send_heartbeat()

    mock_client.services.heartbeat.assert_not_called()
