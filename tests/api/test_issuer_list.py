"""Issuer selection for realm-scoped local deployments."""

from types import SimpleNamespace

import pytest

from service_ml_forecast import dependencies
from service_ml_forecast.config import ENV


def test_master_admin_issuer_is_accepted_with_accessible_tenant(monkeypatch: pytest.MonkeyPatch) -> None:
    class LocalService:
        def get_accessible_realms(self) -> list[SimpleNamespace]:
            return [SimpleNamespace(name="gems")]

    monkeypatch.setattr(dependencies, "get_openremote_service", lambda: LocalService())
    monkeypatch.setattr(ENV, "ML_OR_ISSUER_URL", "https://localhost/auth")

    assert dependencies.get_openremote_issuers() == [
        "https://localhost/auth/realms/master",
        "https://localhost/auth/realms/gems",
    ]
