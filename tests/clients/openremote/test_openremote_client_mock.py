import time
from http import HTTPStatus

import respx

from service_ml_forecast.clients.openremote.models import Asset, AssetDatapoint, AssetDatapointPeriod
from service_ml_forecast.clients.openremote.openremote_client import OpenRemoteClient

# Import shared test data and mock data from conftest.py
from tests.conftest import (
    MOCK_OPENREMOTE_URL,
    TEST_ASSET_ID,
    TEST_ATTRIBUTE_NAME,
    TEST_OLDEST_TIMESTAMP,
)


def test_retrieve_assets(mock_openremote_client: OpenRemoteClient) -> None:
    """Test retrieving assets."""
    mock_power_value = 100

    with respx.mock(base_url=MOCK_OPENREMOTE_URL) as respx_mock:
        respx_mock.post("/api/master/asset/query").mock(
            return_value=respx.MockResponse(
                HTTPStatus.OK,
                json=[
                    {
                        "id": TEST_ASSET_ID,
                        "realm": "master",
                        "attributes": {
                            TEST_ATTRIBUTE_NAME: {
                                "name": TEST_ATTRIBUTE_NAME,
                                "value": mock_power_value,
                                "timestamp": int(time.time() * 1000),
                            }
                        },
                    }
                ],
            )
        )
        assets: list[Asset] = mock_openremote_client.retrieve_assets("master")
        assert len(assets) > 0
        assert assets[0].id == TEST_ASSET_ID


def test_retrieve_assets_invalid_realm(mock_openremote_client: OpenRemoteClient) -> None:
    """Test retrieving assets with invalid realm."""
    with respx.mock(base_url=MOCK_OPENREMOTE_URL) as respx_mock:
        respx_mock.post("/api/invalid_realm_name/asset/query").mock(
            return_value=respx.MockResponse(HTTPStatus.NOT_FOUND)
        )
        assets: list[Asset] = mock_openremote_client.retrieve_assets("invalid_realm_name")
        assert len(assets) == 0


def test_retrieve_asset_datapoint_period(mock_openremote_client: OpenRemoteClient) -> None:
    """Test retrieving asset datapoint period."""
    with respx.mock(base_url=MOCK_OPENREMOTE_URL) as respx_mock:
        respx_mock.get(
            f"/api/master/asset/datapoint/periods?assetId={TEST_ASSET_ID}&attributeName={TEST_ATTRIBUTE_NAME}"
        ).mock(
            return_value=respx.MockResponse(
                HTTPStatus.OK,
                json={
                    "assetId": TEST_ASSET_ID,
                    "attributeName": TEST_ATTRIBUTE_NAME,
                    "oldestTimestamp": TEST_OLDEST_TIMESTAMP,
                    "latestTimestamp": int(time.time() * 1000),
                },
            )
        )
        datapoint_period: AssetDatapointPeriod | None = mock_openremote_client.retrieve_asset_datapoint_period(
            TEST_ASSET_ID, TEST_ATTRIBUTE_NAME
        )
        assert datapoint_period is not None
        assert datapoint_period.assetId == TEST_ASSET_ID
        assert datapoint_period.attributeName == TEST_ATTRIBUTE_NAME


def test_retrieve_asset_datapoint_period_invalid_asset_id(mock_openremote_client: OpenRemoteClient) -> None:
    """Test retrieving asset datapoint period with invalid asset ID."""
    with respx.mock(base_url=MOCK_OPENREMOTE_URL) as respx_mock:
        respx_mock.get(
            f"/api/master/asset/datapoint/periods?assetId=invalid_asset_id&attributeName={TEST_ATTRIBUTE_NAME}"
        ).mock(return_value=respx.MockResponse(HTTPStatus.NOT_FOUND))

        datapoint_period: AssetDatapointPeriod | None = mock_openremote_client.retrieve_asset_datapoint_period(
            "invalid_asset_id", TEST_ATTRIBUTE_NAME
        )
        assert datapoint_period is None


def test_retrieve_historical_datapoints(mock_openremote_client: OpenRemoteClient) -> None:
    """Test retrieving historical datapoints."""
    mock_values = [100, 200]

    with respx.mock(base_url=MOCK_OPENREMOTE_URL) as respx_mock:
        respx_mock.post(f"/api/master/asset/datapoint/{TEST_ASSET_ID}/{TEST_ATTRIBUTE_NAME}").mock(
            return_value=respx.MockResponse(
                HTTPStatus.OK,
                json=[
                    {"x": TEST_OLDEST_TIMESTAMP, "y": mock_values[0]},
                    {"x": TEST_OLDEST_TIMESTAMP + 1, "y": mock_values[1]},
                ],
            )
        )
        datapoints: list[AssetDatapoint] = mock_openremote_client.retrieve_historical_datapoints(
            TEST_ASSET_ID, TEST_ATTRIBUTE_NAME, TEST_OLDEST_TIMESTAMP, int(time.time() * 1000)
        )
        assert len(datapoints) > 0
        assert datapoints[0].x == TEST_OLDEST_TIMESTAMP
        assert datapoints[0].y == mock_values[0]


def test_retrieve_historical_datapoints_invalid_asset_id(mock_openremote_client: OpenRemoteClient) -> None:
    """Test retrieving historical datapoints with invalid asset ID."""
    with respx.mock(base_url=MOCK_OPENREMOTE_URL) as respx_mock:
        respx_mock.post(f"/api/master/asset/datapoint/invalid_asset_id/{TEST_ATTRIBUTE_NAME}").mock(
            return_value=respx.MockResponse(HTTPStatus.NOT_FOUND)
        )
        datapoints: list[AssetDatapoint] = mock_openremote_client.retrieve_historical_datapoints(
            "invalid_asset_id", TEST_ATTRIBUTE_NAME, TEST_OLDEST_TIMESTAMP, int(time.time() * 1000)
        )
        assert len(datapoints) == 0


def test_write_retrieve_predicted_datapoints(mock_openremote_client: OpenRemoteClient) -> None:
    """Test writing and retrieving predicted datapoints."""
    mock_timestamp1 = 572127577200000  # 20100-01-01 00:00:00 UTC
    mock_timestamp2 = mock_timestamp1 + 1  # 20100-01-01 00:00:01 UTC
    mock_values = [100, 200]

    datapoints: list[AssetDatapoint] = [
        AssetDatapoint(x=mock_timestamp1, y=mock_values[0]),
        AssetDatapoint(x=mock_timestamp2, y=mock_values[1]),
    ]

    with respx.mock(base_url=MOCK_OPENREMOTE_URL) as respx_mock:
        respx_mock.put(f"/api/master/asset/predicted/{TEST_ASSET_ID}/{TEST_ATTRIBUTE_NAME}").mock(
            return_value=respx.MockResponse(HTTPStatus.NO_CONTENT)
        )

        respx_mock.post(f"/api/master/asset/predicted/{TEST_ASSET_ID}/{TEST_ATTRIBUTE_NAME}").mock(
            return_value=respx.MockResponse(
                HTTPStatus.OK,
                json=[
                    {"x": mock_timestamp1, "y": mock_values[0]},
                    {"x": mock_timestamp2, "y": mock_values[1]},
                ],
            )
        )

        assert mock_openremote_client.write_predicted_datapoints(TEST_ASSET_ID, TEST_ATTRIBUTE_NAME, datapoints), (
            "Failed to write predicted datapoints"
        )

        predicted_datapoints: list[AssetDatapoint] = mock_openremote_client.retrieve_predicted_datapoints(
            TEST_ASSET_ID, TEST_ATTRIBUTE_NAME, mock_timestamp1, mock_timestamp2
        )
        assert len(predicted_datapoints) == len(datapoints)

        # Sort both lists by timestamp (x) before comparison
        sorted_predicted = sorted(predicted_datapoints, key=lambda d: d.x)
        sorted_original = sorted(datapoints, key=lambda d: d.x)

        for predicted_datapoint, datapoint in zip(sorted_predicted, sorted_original, strict=True):
            assert predicted_datapoint.x == datapoint.x, f"Timestamp mismatch: {predicted_datapoint.x} != {datapoint.x}"
            assert predicted_datapoint.y == datapoint.y, f"Value mismatch: {predicted_datapoint.y} != {datapoint.y}"
