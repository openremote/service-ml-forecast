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


from threading import Event, Thread
from unittest.mock import Mock

import pytest
from openremote_client.models import ServiceInfo, ServiceStatus
from openremote_client.service_registrar import OpenRemoteServiceRegistrar


def test_service_registrar_start() -> None:
    """Test that OpenRemoteServiceRegistrar starts correctly."""
    mock_client = Mock()

    # mock response with the instanceId set to the test-instance-id
    mock_response = ServiceInfo(
        serviceId="test-service",
        instanceId=1,
        label="Test Service",
        homepageUrl="http://localhost:8000/ui",
        status=ServiceStatus.AVAILABLE,
        realm="test-realm",
    )
    mock_client.services.register.return_value = mock_response

    registrar = OpenRemoteServiceRegistrar(
        client=mock_client,
        service_info=ServiceInfo(
            serviceId="test-service",
            label="Test Service",
            homepageUrl="http://localhost:8000/ui",
            status=ServiceStatus.AVAILABLE,
            realm="test-realm",
        ),
    )

    registrar.start()

    assert registrar.registered is True
    assert registrar.instance_id == 1
    assert registrar.scheduler.running is True
    registrar.stop()


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
            realm="test-realm",
        ),
    )
    registrar.instance_id = 1
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
            realm="test-realm",
        ),
    )
    registrar.instance_id = 1
    registrar.registered = True

    registrar._send_heartbeat()

    mock_client.services.heartbeat.assert_called_once_with("test-service", 1)


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
            realm="test-realm",
        ),
    )
    registrar.registered = False

    registrar._send_heartbeat()

    mock_client.services.heartbeat.assert_not_called()


@pytest.mark.parametrize("heartbeat_result", [True, False, None])
def test_only_missing_registration_is_replaced(heartbeat_result: bool | None) -> None:
    client = Mock()
    client.services.heartbeat.return_value = heartbeat_result
    client.services.register.return_value = ServiceInfo(
        serviceId="test-service",
        instanceId=2,
        label="Test Service",
        realm="test-realm",
        homepageUrl="http://localhost:8000/ui",
        status=ServiceStatus.AVAILABLE,
    )
    registrar = OpenRemoteServiceRegistrar(client, client.services.register.return_value)
    registrar.instance_id = 1
    registrar.registered = True

    registrar._send_heartbeat()

    assert client.services.register.call_count == (1 if heartbeat_result is None else 0)
    assert registrar.instance_id == (2 if heartbeat_result is None else 1)


def test_shutdown_waits_for_heartbeat_before_deregistering(monkeypatch: pytest.MonkeyPatch) -> None:
    entered = Event()
    release = Event()
    stopping = Event()
    stopped = Event()
    client = Mock()
    client.services.deregister.return_value = True
    registrar = OpenRemoteServiceRegistrar(
        client,
        ServiceInfo(
            serviceId="test-service",
            label="Test Service",
            realm="test-realm",
            homepageUrl="http://localhost:8000/ui",
            status=ServiceStatus.AVAILABLE,
        ),
    )
    registrar.instance_id = 1
    registrar.registered = True

    def heartbeat(*_args: object) -> bool:
        entered.set()
        assert release.wait(5)
        return False

    def stop() -> None:
        registrar.stop()
        stopped.set()

    shutdown = registrar.scheduler.shutdown

    def shutdown_scheduler() -> None:
        stopping.set()
        shutdown()

    client.services.heartbeat.side_effect = heartbeat
    monkeypatch.setattr(registrar.scheduler, "shutdown", shutdown_scheduler)
    registrar.scheduler.add_job(registrar._send_heartbeat, executor="thread_pool")
    registrar.scheduler.start()
    thread = Thread(target=stop)
    try:
        assert entered.wait(5)
        thread.start()
        assert stopping.wait(5)
        client.services.deregister.assert_not_called()
    finally:
        release.set()
        if thread.ident is not None:
            thread.join(5)
        else:
            registrar.stop()

    assert stopped.is_set()
    client.services.register.assert_not_called()
    client.services.deregister.assert_called_once_with("test-service", 1)
    registrar.stop()
    registrar._send_heartbeat()
    client.services.deregister.assert_called_once_with("test-service", 1)
    client.services.heartbeat.assert_called_once_with("test-service", 1)
