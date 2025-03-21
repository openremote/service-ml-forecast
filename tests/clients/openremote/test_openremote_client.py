import time

import pytest
from httpx import HTTPStatusError

from service_ml_forecast.clients.openremote.models import (
    Asset,
    AssetDatapointPeriod,
    Datapoint,
)
from service_ml_forecast.clients.openremote.openremote_client import OpenRemoteClient

# Common test data used across multiple tests
TEST_ASSET_ID = "44ORIhkDVAlT97dYGUD9n5"
TEST_ATTRIBUTE_NAME = "powerTotalConsumers"


@pytest.fixture
def openremote_client() -> OpenRemoteClient:
    """Create an OpenRemote client for testing against a real instance."""
    from service_ml_forecast.config import config

    client = OpenRemoteClient(
        openremote_url=config.OPENREMOTE_URL,
        keycloak_url=config.OPENREMOTE_KEYCLOAK_URL,
        service_user=config.OPENREMOTE_SERVICE_USER,
        service_user_secret=config.OPENREMOTE_SERVICE_USER_SECRET,
    )

    # Skip tests if OpenRemote API is not available
    if not client.health_check():
        pytest.skip(reason="OpenRemote API not available")

    return client


def test_retrieve_assets(openremote_client: OpenRemoteClient) -> None:
    assets: list[Asset] = openremote_client.retrieve_assets("master")
    assert len(assets) > 0, "No assets retrieved"


def test_retrieve_assets_invalid_realm(openremote_client: OpenRemoteClient) -> None:
    with pytest.raises(HTTPStatusError):
        openremote_client.retrieve_assets("invalid_realm_name")


def test_retrieve_asset_datapoint_period(openremote_client: OpenRemoteClient) -> None:
    datapoint_period: AssetDatapointPeriod = openremote_client.retrieve_asset_datapoint_period(
        TEST_ASSET_ID, TEST_ATTRIBUTE_NAME
    )
    assert datapoint_period is not None, "No asset datapoint period retrieved"


def test_retrieve_asset_datapoint_period_invalid_asset_id(openremote_client: OpenRemoteClient) -> None:
    with pytest.raises(HTTPStatusError):
        openremote_client.retrieve_asset_datapoint_period("invalid_asset_id", TEST_ATTRIBUTE_NAME)


def test_retrieve_historical_datapoints(openremote_client: OpenRemoteClient) -> None:
    datapoints: list[Datapoint] = openremote_client.retrieve_historical_datapoints(
        TEST_ASSET_ID, TEST_ATTRIBUTE_NAME, 1716153600000, int(time.time() * 1000)
    )
    assert len(datapoints) > 0, "No historical datapoints retrieved"


def test_retrieve_historical_datapoints_invalid_asset_id(openremote_client: OpenRemoteClient) -> None:
    with pytest.raises(HTTPStatusError):
        openremote_client.retrieve_historical_datapoints(
            "invalid_asset_id", TEST_ATTRIBUTE_NAME, 1716153600000, int(time.time() * 1000)
        )


def test_write_retrieve_predicted_datapoints(openremote_client: OpenRemoteClient) -> None:
    timestamp1 = 572127577200000  # 20100-01-01 00:00:00
    timestamp2 = timestamp1 + 1  # 20100-01-01 00:00:01

    datapoints: list[Datapoint] = [
        Datapoint(x=timestamp1, y=100),
        Datapoint(x=timestamp2, y=200),
    ]

    assert openremote_client.write_predicted_datapoints(TEST_ASSET_ID, TEST_ATTRIBUTE_NAME, datapoints), (
        "No predicted datapoints written"
    )

    predicted_datapoints: list[Datapoint] = openremote_client.retrieve_predicted_datapoints(
        TEST_ASSET_ID, TEST_ATTRIBUTE_NAME, timestamp1, timestamp2
    )
    assert len(predicted_datapoints) == len(datapoints), (
        "Predicted datapoints should have the same length as the written datapoints"
    )

    # Sort both lists by timestamp (x) before comparison
    sorted_predicted = sorted(predicted_datapoints, key=lambda d: d.x)
    sorted_original = sorted(datapoints, key=lambda d: d.x)

    for predicted_datapoint, datapoint in zip(sorted_predicted, sorted_original, strict=True):
        assert predicted_datapoint.x == datapoint.x, f"Timestamp mismatch: {predicted_datapoint.x} != {datapoint.x}"
        assert predicted_datapoint.y == datapoint.y, f"Value mismatch: {predicted_datapoint.y} != {datapoint.y}"
