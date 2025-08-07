import time
from http import HTTPStatus
from typing import Any

import respx
from openremote_client.models import AssetDatapoint, AssetDatapointPeriod
from openremote_client.rest_client import OpenRemoteClient

from .conftest import (
    MOCK_OPENREMOTE_URL,
    TEST_ASSET_ID,
    TEST_ATTRIBUTE_NAME,
    TEST_OLDEST_TIMESTAMP,
)

# Test constants to avoid magic numbers
EXPECTED_DATAPOINTS_COUNT = 2
EXPECTED_ASSETS_COUNT = 2
EXPECTED_REALMS_COUNT = 2


# helper function to convert seconds to milliseconds
def sec_to_ms(timestamp: int) -> int:
    return int(timestamp * 1000)


def test_health_check_success(mock_openremote_client: OpenRemoteClient) -> None:
    """Test successful health check.

    Verifies that:
    - The client can perform a health check
    - The method returns True when the API is healthy
    """
    with respx.mock(base_url=MOCK_OPENREMOTE_URL) as respx_mock:
        respx_mock.get("/api/master/health").mock(
            return_value=respx.MockResponse(HTTPStatus.OK),
        )
        assert mock_openremote_client.health.check() is True


def test_health_check_failure(mock_openremote_client: OpenRemoteClient) -> None:
    """Test health check failure.

    Verifies that:
    - The client properly handles health check failures
    - The method returns False when the API is not healthy
    """
    with respx.mock(base_url=MOCK_OPENREMOTE_URL) as respx_mock:
        respx_mock.get("/api/master/health").mock(
            return_value=respx.MockResponse(HTTPStatus.INTERNAL_SERVER_ERROR),
        )
        assert mock_openremote_client.health.check() is False


def test_get_asset_datapoint_period(mock_openremote_client: OpenRemoteClient) -> None:
    """Test retrieval of datapoint period information for an asset attribute.

    Verifies that:
    - The client can retrieve time period information for datapoints
    - The response is properly parsed into an AssetDatapointPeriod object
    - The returned object contains the correct asset ID and attribute name
    """
    # Mock asset datapoint period endpoint
    with respx.mock(base_url=MOCK_OPENREMOTE_URL) as respx_mock:
        respx_mock.get(
            f"/api/master/asset/datapoint/periods?assetId={TEST_ASSET_ID}&attributeName={TEST_ATTRIBUTE_NAME}",
        ).mock(
            return_value=respx.MockResponse(
                HTTPStatus.OK,
                json={
                    "assetId": TEST_ASSET_ID,
                    "attributeName": TEST_ATTRIBUTE_NAME,
                    "oldestTimestamp": TEST_OLDEST_TIMESTAMP,
                    "latestTimestamp": sec_to_ms(int(time.time())),
                },
            ),
        )
        datapoint_period: AssetDatapointPeriod | None = mock_openremote_client.assets.get_datapoint_period(
            TEST_ASSET_ID,
            TEST_ATTRIBUTE_NAME,
        )
        assert datapoint_period is not None
        assert datapoint_period.assetId == TEST_ASSET_ID
        assert datapoint_period.attributeName == TEST_ATTRIBUTE_NAME


def test_get_asset_datapoint_period_invalid_asset_id(mock_openremote_client: OpenRemoteClient) -> None:
    """Test datapoint period retrieval with an invalid asset ID.

    Verifies that:
    - The client properly handles a NOT_FOUND response for invalid asset IDs
    - The method returns None when the asset doesn't exist
    """
    # Mock asset datapoint period endpoint
    with respx.mock(base_url=MOCK_OPENREMOTE_URL) as respx_mock:
        respx_mock.get(
            f"/api/master/asset/datapoint/periods?assetId=invalid_asset_id&attributeName={TEST_ATTRIBUTE_NAME}",
        ).mock(return_value=respx.MockResponse(HTTPStatus.NOT_FOUND))

        datapoint_period: AssetDatapointPeriod | None = mock_openremote_client.assets.get_datapoint_period(
            "invalid_asset_id",
            TEST_ATTRIBUTE_NAME,
        )
        assert datapoint_period is None


def test_get_historical_datapoints(mock_openremote_client: OpenRemoteClient) -> None:
    """Test retrieval of historical datapoints for an asset attribute.

    Verifies that:
    - The client can retrieve historical time series data
    - The response is properly parsed into AssetDatapoint objects
    - The returned datapoints have the expected timestamps and values
    """
    # Mock historical datapoints endpoint
    mock_values = [100, 200]

    with respx.mock(base_url=MOCK_OPENREMOTE_URL) as respx_mock:
        respx_mock.post(f"/api/master/asset/datapoint/{TEST_ASSET_ID}/{TEST_ATTRIBUTE_NAME}").mock(
            return_value=respx.MockResponse(
                HTTPStatus.OK,
                json=[
                    {"x": TEST_OLDEST_TIMESTAMP, "y": mock_values[0]},
                    {"x": TEST_OLDEST_TIMESTAMP + 1, "y": mock_values[1]},
                ],
            ),
        )
        datapoints: list[AssetDatapoint] | None = mock_openremote_client.assets.get_historical_datapoints(
            TEST_ASSET_ID,
            TEST_ATTRIBUTE_NAME,
            TEST_OLDEST_TIMESTAMP,
            sec_to_ms(int(time.time())),
        )
        assert datapoints is not None
        assert len(datapoints) > 0
        assert datapoints[0].x == TEST_OLDEST_TIMESTAMP
        assert datapoints[0].y == mock_values[0]


def test_get_historical_datapoints_invalid_asset_id(mock_openremote_client: OpenRemoteClient) -> None:
    """Test historical datapoint retrieval with an invalid asset ID.

    Verifies that:
    - The client properly handles a NOT_FOUND response for invalid asset IDs
    - The method returns None when the asset doesn't exist
    """
    # Mock historical datapoints endpoint
    with respx.mock(base_url=MOCK_OPENREMOTE_URL) as respx_mock:
        respx_mock.post(f"/api/master/asset/datapoint/invalid_asset_id/{TEST_ATTRIBUTE_NAME}").mock(
            return_value=respx.MockResponse(HTTPStatus.NOT_FOUND),
        )
        datapoints: list[AssetDatapoint] | None = mock_openremote_client.assets.get_historical_datapoints(
            "invalid_asset_id",
            TEST_ATTRIBUTE_NAME,
            TEST_OLDEST_TIMESTAMP,
            sec_to_ms(int(time.time())),
        )
        assert datapoints is None


def test_write_predicted_datapoints(mock_openremote_client: OpenRemoteClient) -> None:
    """Test writing and retrieving predicted datapoints for an asset attribute.

    Verifies that:
    - The client can write predicted datapoints to OpenRemote
    - The client can retrieve previously written predicted datapoints
    - The retrieved datapoints match the originally written ones in both timestamps and values
    """
    # Mock predicted datapoints endpoint
    mock_timestamp1 = 572127577200000  # 20100-01-01 00:00:00 UTC
    mock_timestamp2 = mock_timestamp1 + 1  # 20100-01-01 00:00:01 UTC
    mock_values = [100, 200]

    datapoints: list[AssetDatapoint] = [
        AssetDatapoint(x=mock_timestamp1, y=mock_values[0]),
        AssetDatapoint(x=mock_timestamp2, y=mock_values[1]),
    ]

    with respx.mock(base_url=MOCK_OPENREMOTE_URL) as respx_mock:
        respx_mock.put(f"/api/master/asset/predicted/{TEST_ASSET_ID}/{TEST_ATTRIBUTE_NAME}").mock(
            return_value=respx.MockResponse(HTTPStatus.NO_CONTENT),
        )

        respx_mock.post(f"/api/master/asset/predicted/{TEST_ASSET_ID}/{TEST_ATTRIBUTE_NAME}").mock(
            return_value=respx.MockResponse(
                HTTPStatus.OK,
                json=[
                    {"x": mock_timestamp1, "y": mock_values[0]},
                    {"x": mock_timestamp2, "y": mock_values[1]},
                ],
            ),
        )

        assert mock_openremote_client.assets.write_predicted_datapoints(
            TEST_ASSET_ID, TEST_ATTRIBUTE_NAME, datapoints
        ), "Failed to write predicted datapoints"

        predicted_datapoints: list[AssetDatapoint] | None = mock_openremote_client.assets.get_predicted_datapoints(
            TEST_ASSET_ID,
            TEST_ATTRIBUTE_NAME,
            mock_timestamp1,
            mock_timestamp2,
        )
        assert predicted_datapoints is not None
        assert len(predicted_datapoints) == len(datapoints)

        # Sort both lists by timestamp (x) before comparison
        sorted_predicted = sorted(predicted_datapoints, key=lambda d: d.x)
        sorted_original = sorted(datapoints, key=lambda d: d.x)

        for predicted_datapoint, datapoint in zip(sorted_predicted, sorted_original, strict=True):
            assert predicted_datapoint.x == datapoint.x, f"Timestamp mismatch: {predicted_datapoint.x} != {datapoint.x}"
            assert predicted_datapoint.y == datapoint.y, f"Value mismatch: {predicted_datapoint.y} != {datapoint.y}"


def test_write_predicted_datapoints_failure(mock_openremote_client: OpenRemoteClient) -> None:
    """Test writing predicted datapoints failure.

    Verifies that:
    - The client properly handles write failures
    - The method returns False when write fails
    """
    datapoints: list[AssetDatapoint] = [
        AssetDatapoint(x=572127577200000, y=100),
    ]

    with respx.mock(base_url=MOCK_OPENREMOTE_URL) as respx_mock:
        respx_mock.put(f"/api/master/asset/predicted/{TEST_ASSET_ID}/{TEST_ATTRIBUTE_NAME}").mock(
            return_value=respx.MockResponse(HTTPStatus.INTERNAL_SERVER_ERROR),
        )

        assert (
            mock_openremote_client.assets.write_predicted_datapoints(TEST_ASSET_ID, TEST_ATTRIBUTE_NAME, datapoints)
            is False
        )


def test_get_predicted_datapoints(mock_openremote_client: OpenRemoteClient) -> None:
    """Test retrieval of predicted datapoints.

    Verifies that:
    - The client can retrieve predicted datapoints
    - The response is properly parsed into AssetDatapoint objects
    """
    mock_timestamp1 = 572127577200000
    mock_timestamp2 = mock_timestamp1 + 1
    mock_values = [100, 200]

    with respx.mock(base_url=MOCK_OPENREMOTE_URL) as respx_mock:
        respx_mock.post(f"/api/master/asset/predicted/{TEST_ASSET_ID}/{TEST_ATTRIBUTE_NAME}").mock(
            return_value=respx.MockResponse(
                HTTPStatus.OK,
                json=[
                    {"x": mock_timestamp1, "y": mock_values[0]},
                    {"x": mock_timestamp2, "y": mock_values[1]},
                ],
            ),
        )

        predicted_datapoints: list[AssetDatapoint] | None = mock_openremote_client.assets.get_predicted_datapoints(
            TEST_ASSET_ID,
            TEST_ATTRIBUTE_NAME,
            mock_timestamp1,
            mock_timestamp2,
        )
        assert predicted_datapoints is not None
        assert len(predicted_datapoints) == EXPECTED_DATAPOINTS_COUNT
        assert predicted_datapoints[0].x == mock_timestamp1
        assert predicted_datapoints[0].y == mock_values[0]
        assert predicted_datapoints[1].x == mock_timestamp2
        assert predicted_datapoints[1].y == mock_values[1]


def test_get_predicted_datapoints_not_found(mock_openremote_client: OpenRemoteClient) -> None:
    """Test retrieval of predicted datapoints when not found.

    Verifies that:
    - The client properly handles NOT_FOUND responses
    - The method returns None when no predicted datapoints exist
    """
    with respx.mock(base_url=MOCK_OPENREMOTE_URL) as respx_mock:
        respx_mock.post(f"/api/master/asset/predicted/{TEST_ASSET_ID}/{TEST_ATTRIBUTE_NAME}").mock(
            return_value=respx.MockResponse(HTTPStatus.NOT_FOUND),
        )

        predicted_datapoints: list[AssetDatapoint] | None = mock_openremote_client.assets.get_predicted_datapoints(
            TEST_ASSET_ID,
            TEST_ATTRIBUTE_NAME,
            572127577200000,
            572127577200001,
        )
        assert predicted_datapoints is None


def test_asset_query(mock_openremote_client: OpenRemoteClient) -> None:
    """Test asset query functionality.

    Verifies that:
    - The client can perform asset queries
    - The response is properly parsed into BasicAsset objects
    """
    asset_query = {
        "recursive": True,
        "realm": {"name": "test_realm"},
        "ids": ["asset1", "asset2"],
    }

    mock_assets: list[dict[str, Any]] = [
        {
            "id": "asset1",
            "name": "Test Asset 1",
            "realm": "test_realm",
            "parentId": None,
            "attributes": {},
        },
        {
            "id": "asset2",
            "name": "Test Asset 2",
            "realm": "test_realm",
            "parentId": "asset1",
            "attributes": {},
        },
    ]

    with respx.mock(base_url=MOCK_OPENREMOTE_URL) as respx_mock:
        respx_mock.post("/api/master/asset/query").mock(
            return_value=respx.MockResponse(HTTPStatus.OK, json=mock_assets),
        )

        assets = mock_openremote_client.assets.query(asset_query, "test_realm")
        assert assets is not None
        assert len(assets) == EXPECTED_ASSETS_COUNT
        assert assets[0].id == "asset1"
        assert assets[0].name == "Test Asset 1"
        assert assets[1].id == "asset2"
        assert assets[1].name == "Test Asset 2"


def test_asset_query_failure(mock_openremote_client: OpenRemoteClient) -> None:
    """Test asset query failure.

    Verifies that:
    - The client properly handles query failures
    - The method returns None when query fails
    """
    asset_query = {
        "recursive": True,
        "realm": {"name": "test_realm"},
        "ids": ["asset1"],
    }

    with respx.mock(base_url=MOCK_OPENREMOTE_URL) as respx_mock:
        respx_mock.post("/api/master/asset/query").mock(
            return_value=respx.MockResponse(HTTPStatus.INTERNAL_SERVER_ERROR),
        )

        assets = mock_openremote_client.assets.query(asset_query, "test_realm")
        assert assets is None


def test_get_assets_by_ids(mock_openremote_client: OpenRemoteClient) -> None:
    """Test retrieving assets by IDs.

    Verifies that:
    - The client can retrieve assets by their IDs
    - The method uses the correct query structure
    - The response is properly parsed into BasicAsset objects
    """
    asset_ids = ["asset1", "asset2"]
    query_realm = "test_realm"

    mock_assets: list[dict[str, Any]] = [
        {
            "id": "asset1",
            "name": "Test Asset 1",
            "realm": query_realm,
            "parentId": None,
            "attributes": {},
        },
        {
            "id": "asset2",
            "name": "Test Asset 2",
            "realm": query_realm,
            "parentId": None,
            "attributes": {},
        },
    ]

    with respx.mock(base_url=MOCK_OPENREMOTE_URL) as respx_mock:
        respx_mock.post("/api/master/asset/query").mock(
            return_value=respx.MockResponse(HTTPStatus.OK, json=mock_assets),
        )

        assets = mock_openremote_client.assets.get_by_ids(asset_ids, query_realm)
        assert assets is not None
        assert len(assets) == EXPECTED_ASSETS_COUNT
        assert assets[0].id == "asset1"
        assert assets[1].id == "asset2"


def test_get_assets_by_ids_failure(mock_openremote_client: OpenRemoteClient) -> None:
    """Test retrieving assets by IDs failure.

    Verifies that:
    - The client properly handles failures when retrieving assets by IDs
    - The method returns None when the operation fails
    """
    asset_ids = ["asset1"]
    query_realm = "test_realm"

    with respx.mock(base_url=MOCK_OPENREMOTE_URL) as respx_mock:
        respx_mock.post("/api/master/asset/query").mock(
            return_value=respx.MockResponse(HTTPStatus.NOT_FOUND),
        )

        assets = mock_openremote_client.assets.get_by_ids(asset_ids, query_realm)
        assert assets is None


def test_get_realms(mock_openremote_client: OpenRemoteClient) -> None:
    """Test retrieving realms.

    Verifies that:
    - The client can retrieve realms
    - The response is properly parsed into Realm objects
    """
    mock_realms: list[dict[str, Any]] = [
        {
            "name": "test_realm_1",
            "displayName": "Test Realm 1",
        },
        {
            "name": "test_realm_2",
            "displayName": "Test Realm 2",
        },
    ]

    with respx.mock(base_url=MOCK_OPENREMOTE_URL) as respx_mock:
        respx_mock.get("/api/master/realm/accessible").mock(
            return_value=respx.MockResponse(HTTPStatus.OK, json=mock_realms),
        )

        realms = mock_openremote_client.realms.get_accessible()
        assert realms is not None
        assert len(realms) == EXPECTED_REALMS_COUNT
        assert realms[0].name == "test_realm_1"
        assert realms[1].name == "test_realm_2"


def test_get_realms_failure(mock_openremote_client: OpenRemoteClient) -> None:
    """Test retrieving realms failure.

    Verifies that:
    - The client properly handles failures when retrieving realms
    - The method returns None when the operation fails
    """
    with respx.mock(base_url=MOCK_OPENREMOTE_URL) as respx_mock:
        respx_mock.get("/api/master/realm/accessible").mock(
            return_value=respx.MockResponse(HTTPStatus.INTERNAL_SERVER_ERROR),
        )

        realms = mock_openremote_client.realms.get_accessible()
        assert realms is None
