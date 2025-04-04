import time

from service_ml_forecast.clients.openremote.models import Asset, AssetDatapoint, AssetDatapointPeriod
from service_ml_forecast.clients.openremote.openremote_client import OpenRemoteClient
from service_ml_forecast.common.time_util import TimeUtil
from tests.conftest import TEST_ASSET_ID, TEST_ATTRIBUTE_NAME


def test_retrieve_assets(openremote_client: OpenRemoteClient) -> None:
    """Test retrieval of assets from a real OpenRemote instance.

    Verifies that:
    - The client can successfully connect to and retrieve assets from OpenRemote
    - The response contains at least one valid asset
    """
    assets: list[Asset] | None = openremote_client.retrieve_assets("master")
    assert assets is not None
    assert len(assets) > 0


def test_retrieve_assets_invalid_realm(openremote_client: OpenRemoteClient) -> None:
    """Test asset retrieval behavior with an invalid realm on a real instance.

    Verifies that:
    - The client properly handles errors when an invalid realm is specified
    - The method returns None for non-existent realms
    """
    assets: list[Asset] | None = openremote_client.retrieve_assets("invalid_realm_name")
    assert assets is None


def test_retrieve_asset_datapoint_period(openremote_client: OpenRemoteClient) -> None:
    """Test retrieval of datapoint period information from a real OpenRemote instance.

    Verifies that:
    - The client can retrieve time period metadata for asset datapoints
    - The returned object contains valid period information
    """
    datapoint_period: AssetDatapointPeriod | None = openremote_client.retrieve_asset_datapoint_period(
        TEST_ASSET_ID,
        TEST_ATTRIBUTE_NAME,
    )
    assert datapoint_period is not None


def test_retrieve_asset_datapoint_period_invalid_asset_id(openremote_client: OpenRemoteClient) -> None:
    """Test datapoint period retrieval with an invalid asset ID on a real instance.

    Verifies that:
    - The client properly handles errors for non-existent assets
    - The method returns None when the asset ID is invalid
    """
    datapoint_period: AssetDatapointPeriod | None = openremote_client.retrieve_asset_datapoint_period(
        "invalid_asset_id",
        TEST_ATTRIBUTE_NAME,
    )
    assert datapoint_period is None


def test_retrieve_historical_datapoints(openremote_client: OpenRemoteClient) -> None:
    """Test retrieval of historical datapoints from a real OpenRemote instance.

    Verifies that:
    - The client can retrieve time series data from OpenRemote
    - The response contains valid datapoints for the given time range
    """
    datapoints: list[AssetDatapoint] | None = openremote_client.retrieve_historical_datapoints(
        TEST_ASSET_ID,
        TEST_ATTRIBUTE_NAME,
        1716153600000,
        TimeUtil.sec_to_ms(int(time.time())),
    )
    assert datapoints is not None
    assert len(datapoints) > 0


def test_retrieve_historical_datapoints_invalid_asset_id(openremote_client: OpenRemoteClient) -> None:
    """Test historical datapoint retrieval with an invalid asset ID on a real instance.

    Verifies that:
    - The client properly handles errors for non-existent assets
    - The method returns None when the asset ID is invalid
    """
    datapoints: list[AssetDatapoint] | None = openremote_client.retrieve_historical_datapoints(
        "invalid_asset_id",
        TEST_ATTRIBUTE_NAME,
        1716153600000,
        TimeUtil.sec_to_ms(int(time.time())),
    )
    assert datapoints is None, "Expected the datapoints to be None"


def test_write_retrieve_predicted_datapoints(openremote_client: OpenRemoteClient) -> None:
    """Test writing and retrieving predicted datapoints on a real OpenRemote instance.

    Verifies that:
    - The client can write predicted datapoints to OpenRemote
    - The client can retrieve those predictions within a specified time range
    - The retrieved predictions maintain the same timestamps and values
    """
    timestamp1 = 572127577200000  # 20100-01-01 00:00:00
    timestamp2 = timestamp1 + 1  # 20100-01-01 00:00:01

    datapoints: list[AssetDatapoint] = [
        AssetDatapoint(x=timestamp1, y=100),
        AssetDatapoint(x=timestamp2, y=200),
    ]

    assert openremote_client.write_predicted_datapoints(TEST_ASSET_ID, TEST_ATTRIBUTE_NAME, datapoints)

    predicted_datapoints: list[AssetDatapoint] | None = openremote_client.retrieve_predicted_datapoints(
        TEST_ASSET_ID,
        TEST_ATTRIBUTE_NAME,
        timestamp1,
        timestamp2,
    )
    assert predicted_datapoints is not None
    assert len(predicted_datapoints) == len(datapoints)

    # Sort both lists by timestamp (x) before comparison
    sorted_predicted = sorted(predicted_datapoints, key=lambda d: d.x)
    sorted_original = sorted(datapoints, key=lambda d: d.x)

    for predicted_datapoint, datapoint in zip(sorted_predicted, sorted_original, strict=True):
        assert predicted_datapoint.x == datapoint.x, f"Timestamp mismatch: {predicted_datapoint.x} != {datapoint.x}"
        assert predicted_datapoint.y == datapoint.y, f"Value mismatch: {predicted_datapoint.y} != {datapoint.y}"
