import time
from http import HTTPStatus

import pytest
import respx
from httpx import HTTPStatusError

from service_ml_forecast.clients.openremote.models import Asset, AssetDatapoint, AssetDatapointPeriod
from service_ml_forecast.clients.openremote.openremote_client import OpenRemoteClient

# Mock URLs and credentials - used in openremote_client fixture and all tests
MOCK_OPENREMOTE_URL = "https://openremote.local"
MOCK_KEYCLOAK_URL = "https://keycloak.local"
MOCK_SERVICE_USER = "service_user"
MOCK_SERVICE_USER_SECRET = "service_user_secret"
MOCK_ACCESS_TOKEN = "mock_access_token"
MOCK_TOKEN_EXPIRY_SECONDS = 60

# Common test data used across multiple tests
MOCK_ASSET_ID = "44ORIhkDVAlT97dYGUD9n5"
MOCK_ATTRIBUTE_NAME = "powerTotalConsumers"
MOCK_OLDEST_TIMESTAMP = 1716153600000  # 2024-05-20 00:00:00 UTC


@pytest.fixture
def openremote_client() -> OpenRemoteClient:
    """Create a mock OpenRemote client with mocked authentication."""
    with respx.mock(base_url=MOCK_KEYCLOAK_URL) as respx_mock:
        # Mock the token endpoint
        respx_mock.post("/auth/realms/master/protocol/openid-connect/token").mock(
            return_value=respx.MockResponse(
                HTTPStatus.OK,
                json={
                    "access_token": MOCK_ACCESS_TOKEN,
                    "token_type": "Bearer",
                    "expires_in": MOCK_TOKEN_EXPIRY_SECONDS,
                },
            )
        )

        client = OpenRemoteClient(
            openremote_url=MOCK_OPENREMOTE_URL,
            keycloak_url=MOCK_KEYCLOAK_URL,
            service_user=MOCK_SERVICE_USER,
            service_user_secret=MOCK_SERVICE_USER_SECRET,
        )
        return client


def test_retrieve_assets(openremote_client: OpenRemoteClient) -> None:
    """Test retrieving assets."""
    mock_power_value = 100

    with respx.mock(base_url=MOCK_OPENREMOTE_URL) as respx_mock:
        respx_mock.post("/api/master/asset/query").mock(
            return_value=respx.MockResponse(
                HTTPStatus.OK,
                json=[
                    {
                        "id": MOCK_ASSET_ID,
                        "realm": "master",
                        "attributes": {
                            MOCK_ATTRIBUTE_NAME: {
                                "name": MOCK_ATTRIBUTE_NAME,
                                "value": mock_power_value,
                                "timestamp": int(time.time() * 1000),
                            }
                        },
                    }
                ],
            )
        )
        assets: list[Asset] = openremote_client.retrieve_assets("master")
        assert len(assets) > 0
        assert assets[0].id == MOCK_ASSET_ID


def test_retrieve_assets_invalid_realm(openremote_client: OpenRemoteClient) -> None:
    """Test retrieving assets with invalid realm."""
    with respx.mock(base_url=MOCK_OPENREMOTE_URL) as respx_mock:
        respx_mock.post("/api/invalid_realm_name/asset/query").mock(
            return_value=respx.MockResponse(HTTPStatus.NOT_FOUND)
        )
        with pytest.raises(HTTPStatusError):
            openremote_client.retrieve_assets("invalid_realm_name")


def test_retrieve_asset_datapoint_period(openremote_client: OpenRemoteClient) -> None:
    """Test retrieving asset datapoint period."""
    with respx.mock(base_url=MOCK_OPENREMOTE_URL) as respx_mock:
        respx_mock.get(
            f"/api/master/asset/datapoint/periods?assetId={MOCK_ASSET_ID}&attributeName={MOCK_ATTRIBUTE_NAME}"
        ).mock(
            return_value=respx.MockResponse(
                HTTPStatus.OK,
                json={
                    "assetId": MOCK_ASSET_ID,
                    "attributeName": MOCK_ATTRIBUTE_NAME,
                    "oldestTimestamp": MOCK_OLDEST_TIMESTAMP,
                    "latestTimestamp": int(time.time() * 1000),
                },
            )
        )
        datapoint_period: AssetDatapointPeriod = openremote_client.retrieve_asset_datapoint_period(
            MOCK_ASSET_ID, MOCK_ATTRIBUTE_NAME
        )
        assert datapoint_period is not None
        assert datapoint_period.assetId == MOCK_ASSET_ID
        assert datapoint_period.attributeName == MOCK_ATTRIBUTE_NAME


def test_retrieve_asset_datapoint_period_invalid_asset_id(openremote_client: OpenRemoteClient) -> None:
    """Test retrieving asset datapoint period with invalid asset ID."""
    with respx.mock(base_url=MOCK_OPENREMOTE_URL) as respx_mock:
        respx_mock.get(
            f"/api/master/asset/datapoint/periods?assetId=invalid_asset_id&attributeName={MOCK_ATTRIBUTE_NAME}"
        ).mock(return_value=respx.MockResponse(HTTPStatus.NOT_FOUND))
        with pytest.raises(HTTPStatusError):
            openremote_client.retrieve_asset_datapoint_period("invalid_asset_id", MOCK_ATTRIBUTE_NAME)


def test_retrieve_historical_datapoints(openremote_client: OpenRemoteClient) -> None:
    """Test retrieving historical datapoints."""
    mock_values = [100, 200]

    with respx.mock(base_url=MOCK_OPENREMOTE_URL) as respx_mock:
        respx_mock.post(f"/api/master/asset/datapoint/{MOCK_ASSET_ID}/{MOCK_ATTRIBUTE_NAME}").mock(
            return_value=respx.MockResponse(
                HTTPStatus.OK,
                json=[
                    {"x": MOCK_OLDEST_TIMESTAMP, "y": mock_values[0]},
                    {"x": MOCK_OLDEST_TIMESTAMP + 1, "y": mock_values[1]},
                ],
            )
        )
        datapoints: list[AssetDatapoint] = openremote_client.retrieve_historical_datapoints(
            MOCK_ASSET_ID, MOCK_ATTRIBUTE_NAME, MOCK_OLDEST_TIMESTAMP, int(time.time() * 1000)
        )
        assert len(datapoints) > 0
        assert datapoints[0].x == MOCK_OLDEST_TIMESTAMP
        assert datapoints[0].y == mock_values[0]


def test_retrieve_historical_datapoints_invalid_asset_id(openremote_client: OpenRemoteClient) -> None:
    """Test retrieving historical datapoints with invalid asset ID."""
    with respx.mock(base_url=MOCK_OPENREMOTE_URL) as respx_mock:
        respx_mock.post(f"/api/master/asset/datapoint/invalid_asset_id/{MOCK_ATTRIBUTE_NAME}").mock(
            return_value=respx.MockResponse(HTTPStatus.NOT_FOUND)
        )
        with pytest.raises(HTTPStatusError):
            openremote_client.retrieve_historical_datapoints(
                "invalid_asset_id", MOCK_ATTRIBUTE_NAME, MOCK_OLDEST_TIMESTAMP, int(time.time() * 1000)
            )


def test_write_retrieve_predicted_datapoints(openremote_client: OpenRemoteClient) -> None:
    """Test writing and retrieving predicted datapoints."""
    mock_timestamp1 = 572127577200000  # 20100-01-01 00:00:00 UTC
    mock_timestamp2 = mock_timestamp1 + 1  # 20100-01-01 00:00:01 UTC
    mock_values = [100, 200]

    datapoints: list[AssetDatapoint] = [
        AssetDatapoint(x=mock_timestamp1, y=mock_values[0]),
        AssetDatapoint(x=mock_timestamp2, y=mock_values[1]),
    ]

    with respx.mock(base_url=MOCK_OPENREMOTE_URL) as respx_mock:
        respx_mock.put(f"/api/master/asset/predicted/{MOCK_ASSET_ID}/{MOCK_ATTRIBUTE_NAME}").mock(
            return_value=respx.MockResponse(HTTPStatus.NO_CONTENT)
        )

        respx_mock.post(f"/api/master/asset/predicted/{MOCK_ASSET_ID}/{MOCK_ATTRIBUTE_NAME}").mock(
            return_value=respx.MockResponse(
                HTTPStatus.OK,
                json=[
                    {"x": mock_timestamp1, "y": mock_values[0]},
                    {"x": mock_timestamp2, "y": mock_values[1]},
                ],
            )
        )

        assert openremote_client.write_predicted_datapoints(MOCK_ASSET_ID, MOCK_ATTRIBUTE_NAME, datapoints), (
            "Failed to write predicted datapoints"
        )

        predicted_datapoints: list[AssetDatapoint] = openremote_client.retrieve_predicted_datapoints(
            MOCK_ASSET_ID, MOCK_ATTRIBUTE_NAME, mock_timestamp1, mock_timestamp2
        )
        assert len(predicted_datapoints) == len(datapoints)

        # Sort both lists by timestamp (x) before comparison
        sorted_predicted = sorted(predicted_datapoints, key=lambda d: d.x)
        sorted_original = sorted(datapoints, key=lambda d: d.x)

        for predicted_datapoint, datapoint in zip(sorted_predicted, sorted_original, strict=True):
            assert predicted_datapoint.x == datapoint.x, f"Timestamp mismatch: {predicted_datapoint.x} != {datapoint.x}"
            assert predicted_datapoint.y == datapoint.y, f"Value mismatch: {predicted_datapoint.y} != {datapoint.y}"
