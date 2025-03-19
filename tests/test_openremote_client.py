import time

import pytest
from httpx import HTTPStatusError

from service_ml_forecast.config import config
from service_ml_forecast.integrations.openremote.models import (
    Asset,
    AssetDatapointPeriod,
    Datapoint,
)
from service_ml_forecast.integrations.openremote.openremote_client import OpenRemoteClient

openremote_client = OpenRemoteClient(
    openremote_url=config.OPENREMOTE_URL,
    keycloak_url=config.OPENREMOTE_KEYCLOAK_URL,
    service_user=config.OPENREMOTE_SERVICE_USER,
    service_user_secret=config.OPENREMOTE_SERVICE_USER_SECRET,
)


def test_retrieve_assets() -> None:
    assets: list[Asset] = openremote_client.retrieve_assets("master")
    assert len(assets) > 0


def test_retrieve_assets_invalid_realm() -> None:
    with pytest.raises(HTTPStatusError):
        openremote_client.retrieve_assets("invalid_realm_name")


def test_retrieve_asset_datapoint_period() -> None:
    datapoint_period: AssetDatapointPeriod = openremote_client.retrieve_asset_datapoint_period(
        "44ORIhkDVAlT97dYGUD9n5", "powerTotalConsumers"
    )
    assert datapoint_period is not None


def test_retrieve_asset_datapoint_period_invalid_asset_id() -> None:
    with pytest.raises(HTTPStatusError):
        openremote_client.retrieve_asset_datapoint_period("invalid_asset_id", "powerTotalConsumers")


def test_retrieve_historical_datapoints() -> None:
    datapoints: list[Datapoint] = openremote_client.retrieve_historical_datapoints(
        "44ORIhkDVAlT97dYGUD9n5", "powerTotalConsumers", 1716153600000, int(time.time() * 1000)
    )
    assert len(datapoints) > 0
