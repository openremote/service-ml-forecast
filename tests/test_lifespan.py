from unittest.mock import Mock, call

import pytest
from fastapi.testclient import TestClient

from tests.conftest import get_fresh_app


@pytest.mark.parametrize("failure", [None, "startup", "request", "shutdown"])
def test_background_services_follow_app_lifecycle(monkeypatch: pytest.MonkeyPatch, failure: str | None) -> None:
    app = get_fresh_app(keycloak_enabled=False)
    from service_ml_forecast import main

    services = Mock()
    monkeypatch.setattr(main, "ModelScheduler", Mock(return_value=services.scheduler))
    monkeypatch.setattr(main, "OpenRemoteServiceRegistrar", Mock(return_value=services.registrar))
    if failure == "startup":
        services.registrar.start.side_effect = RuntimeError("startup failed")
    elif failure == "shutdown":
        services.scheduler.stop.side_effect = RuntimeError("shutdown failed")

    def run_app() -> None:
        with TestClient(app):
            services.scheduler.start.assert_called_once_with()
            services.registrar.start.assert_called_once_with()
            if failure == "request":
                raise RuntimeError("request failed")

    if failure is None:
        run_app()
    else:
        with pytest.raises(RuntimeError, match=f"{failure} failed"):
            run_app()

    services.scheduler.stop.assert_called_once_with()
    services.registrar.stop.assert_called_once_with()
    assert services.mock_calls[-2:] == [call.scheduler.stop(), call.registrar.stop()]
