import json
from collections.abc import Iterator
from http import HTTPStatus
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from service_ml_forecast.api.web_route import router
from service_ml_forecast.config import DIRS, ENV


@pytest.fixture
def web_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    web_root = tmp_path / "web"
    web_root.mkdir()
    (web_root / "index.html").write_text("<html>Forecast configuration</html>", encoding="utf-8")
    (web_root / "help.txt").write_text("Forecast help", encoding="utf-8")
    (tmp_path / "private.txt").write_text("Outside the web directory", encoding="utf-8")
    monkeypatch.setattr(DIRS, "ML_WEBSERVER_UI_DIST_DIR", web_root)
    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as client:
        yield client


@pytest.mark.parametrize("path", ["/ui/%2e%2e/private.txt", "/ui/%2e%2e%2fprivate.txt"])
def test_static_files_stay_within_the_web_directory(web_client: TestClient, path: str) -> None:
    response = web_client.get(path)

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert "Outside the web directory" not in response.text


def test_static_files_inside_the_web_directory_are_served(web_client: TestClient) -> None:
    response = web_client.get("/ui/help.txt")

    assert response.status_code == HTTPStatus.OK
    assert response.text == "Forecast help"


def test_client_routes_serve_the_app_index(web_client: TestClient) -> None:
    response = web_client.get("/ui/gems/configs")

    assert response.status_code == HTTPStatus.OK
    assert response.text == "<html>Forecast configuration</html>"


@pytest.mark.parametrize("path", ["/ui/", "/ui/test/configs"])
def test_app_index_uses_runtime_deployment_configuration(
    web_client: TestClient, monkeypatch: pytest.MonkeyPatch, path: str
) -> None:
    (DIRS.ML_WEBSERVER_UI_DIST_DIR / "index.html").write_text("__ML_RUNTIME_CONFIG__", encoding="utf-8")
    monkeypatch.setattr(ENV, "ML_API_ROOT_PATH", "/services/forecast-test")
    monkeypatch.setattr(ENV, "ML_OR_URL", "https://manager.example.test")
    monkeypatch.setattr(ENV, "ML_OR_KEYCLOAK_URL", "https://identity.example.test/auth")

    response = web_client.get(path)

    assert response.status_code == HTTPStatus.OK
    assert json.loads(response.text) == {
        "ML_SERVICE_URL": "/services/forecast-test",
        "ML_OR_URL": "https://manager.example.test",
        "ML_OR_KEYCLOAK_URL": "https://identity.example.test/auth",
    }
