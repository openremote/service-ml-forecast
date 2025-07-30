from unittest.mock import Mock

from openremote_client import AssetDatapoint
from service_ml_forecast.services.openremote_service import OpenRemoteService

# Constants for test values
EXPECTED_CALLS_3_MONTHS = 3
EXPECTED_CALLS_2_MONTHS = 2
EXPECTED_CALLS_4_MONTHS = 4

# Timestamp constants for chunking boundary tests
JAN_1_2024 = 1704067200000  # 2024-01-01 00:00:00 UTC
FEB_1_2024 = 1706745600000  # 2024-02-01 00:00:00 UTC
MAR_1_2024 = 1709251200000  # 2024-03-01 00:00:00 UTC
APR_1_2024 = 1711929600000  # 2024-04-01 00:00:00 UTC


def test_get_historical_datapoints_single_month_no_chunking(mock_openremote_service: OpenRemoteService) -> None:
    """Test that single month requests don't trigger chunking.

    Verifies that:
    - Requests spanning 1 month or less use a single API call
    - No chunking logic is applied for short time periods
    - The client method is called exactly once with the original timestamps
    """
    # Mock the client method
    mock_client = Mock()
    mock_openremote_service.client = mock_client

    # Mock return value for single month
    mock_datapoints = [AssetDatapoint(x=JAN_1_2024, y=100)]
    mock_client.assets.get_historical_datapoints.return_value = mock_datapoints

    # Test single month (Jan 1 to Feb 1)
    from_timestamp = JAN_1_2024  # 2024-01-01 00:00:00 UTC
    to_timestamp = FEB_1_2024  # 2024-02-01 00:00:00 UTC

    result = mock_openremote_service._get_historical_datapoints(
        "test_asset", "test_attribute", from_timestamp, to_timestamp
    )

    # Should call client method once (no chunking)
    mock_client.assets.get_historical_datapoints.assert_called_once_with(
        "test_asset", "test_attribute", from_timestamp, to_timestamp
    )
    assert result == mock_datapoints


def test_get_historical_datapoints_multi_month_chunking(mock_openremote_service: OpenRemoteService) -> None:
    """Test that multi-month requests trigger chunking with correct boundaries.

    Verifies that:
    - Requests spanning more than 1 month are split into monthly chunks
    - Each month gets its own API call to avoid datapoint limits
    - All chunk results are properly combined into a single result
    - Chunk boundaries are correct with no gaps or overlaps
    - First chunk starts at original from_timestamp, last chunk ends at original to_timestamp
    """
    # Mock the client method
    mock_client = Mock()
    mock_openremote_service.client = mock_client

    # Mock return values for chunks
    chunk1_datapoints = [AssetDatapoint(x=JAN_1_2024, y=100)]  # Jan
    chunk2_datapoints = [AssetDatapoint(x=FEB_1_2024, y=200)]  # Feb
    chunk3_datapoints = [AssetDatapoint(x=MAR_1_2024, y=300)]  # Mar

    mock_client.assets.get_historical_datapoints.side_effect = [
        chunk1_datapoints,
        chunk2_datapoints,
        chunk3_datapoints,
    ]

    # Test 3 months (Jan 1 to Apr 1)
    from_timestamp = JAN_1_2024  # 2024-01-01 00:00:00 UTC
    to_timestamp = APR_1_2024  # 2024-04-01 00:00:00 UTC

    result = mock_openremote_service._get_historical_datapoints(
        "test_asset", "test_attribute", from_timestamp, to_timestamp
    )

    # Should call client method 3 times (one for each month)
    assert mock_client.assets.get_historical_datapoints.call_count == EXPECTED_CALLS_3_MONTHS

    # Verify the calls were made with correct timestamps
    calls = mock_client.assets.get_historical_datapoints.call_args_list
    assert len(calls) == EXPECTED_CALLS_3_MONTHS

    # Verify chunk boundaries are correct
    call1_args = calls[0][0]  # (asset_id, attribute_name, from_ts, to_ts)
    call2_args = calls[1][0]
    call3_args = calls[2][0]

    # First chunk: Jan 1 to Feb 1
    assert call1_args[2] == from_timestamp  # 2024-01-01 00:00:00 UTC
    assert call1_args[3] == FEB_1_2024  # 2024-02-01 00:00:00 UTC

    # Second chunk: Feb 1 to Mar 1
    assert call2_args[2] == FEB_1_2024  # 2024-02-01 00:00:00 UTC
    assert call2_args[3] == MAR_1_2024  # 2024-03-01 00:00:00 UTC

    # Third chunk: Mar 1 to Apr 1
    assert call3_args[2] == MAR_1_2024  # 2024-03-01 00:00:00 UTC
    assert call3_args[3] == to_timestamp  # 2024-04-01 00:00:00 UTC

    # Verify no gaps or overlaps between chunks
    assert call1_args[3] == call2_args[2]  # Feb 1 boundary
    assert call2_args[3] == call3_args[2]  # Mar 1 boundary

    # Check that all datapoints are combined
    expected_datapoints = chunk1_datapoints + chunk2_datapoints + chunk3_datapoints
    assert result == expected_datapoints


def test_get_historical_datapoints_chunking_partial_months(mock_openremote_service: OpenRemoteService) -> None:
    """Test chunking with partial months and boundary verification.

    Verifies that:
    - Partial months at the start (Jan 15-31) create a separate API call
    - Full months in the middle (Feb, Mar) each get their own API call
    - Partial months at the end (Apr 1-30) create a separate API call
    - 15 Jan to 30 Apr results in exactly 4 API calls (Jan 15-31, Feb 1-29, Mar 1-31, Apr 1-30)
    - 1 Jan to 1 Apr results in exactly 3 API calls (Jan 1-31, Feb 1-29, Mar 1-31)
    - All datapoints from all chunks are properly combined
    - Chunk boundaries respect the original from_timestamp and to_timestamp limits
    """
    # Mock the client method
    mock_client = Mock()
    mock_openremote_service.client = mock_client

    # Mock return values for chunks
    jan_datapoints = [AssetDatapoint(x=1705276800000, y=100)]  # Jan 15-31
    feb_datapoints = [AssetDatapoint(x=FEB_1_2024, y=200)]  # Feb 1-29
    mar_datapoints = [AssetDatapoint(x=MAR_1_2024, y=300)]  # Mar 1-31
    apr_datapoints = [AssetDatapoint(x=APR_1_2024, y=400)]  # Apr 1-30

    mock_client.assets.get_historical_datapoints.side_effect = [
        jan_datapoints,
        feb_datapoints,
        mar_datapoints,
        apr_datapoints,
    ]

    # Test 15 Jan to 30 Apr (should be 4 API calls)
    from_timestamp = 1705276800000  # 2024-01-15 00:00:00 UTC
    to_timestamp = 1714435200000  # 2024-04-30 00:00:00 UTC

    result = mock_openremote_service._get_historical_datapoints(
        "test_asset", "test_attribute", from_timestamp, to_timestamp
    )

    # Should call client method 4 times (Jan 15-31, Feb 1-29, Mar 1-31, Apr 1-30)
    assert mock_client.assets.get_historical_datapoints.call_count == EXPECTED_CALLS_4_MONTHS

    # Verify the calls were made with correct timestamps
    calls = mock_client.assets.get_historical_datapoints.call_args_list
    assert len(calls) == EXPECTED_CALLS_4_MONTHS

    # Verify boundaries for partial month scenario
    call1_args = calls[0][0]  # First partial chunk
    call4_args = calls[3][0]  # Last partial chunk

    # First chunk starts at original from_timestamp (Jan 15)
    assert call1_args[2] == from_timestamp  # 2024-01-15 00:00:00 UTC

    # Last chunk ends at original to_timestamp (Apr 30), not extended to May 1
    assert call4_args[3] == to_timestamp  # 2024-04-30 00:00:00 UTC

    # Check that all datapoints are combined
    expected_datapoints = jan_datapoints + feb_datapoints + mar_datapoints + apr_datapoints
    assert result == expected_datapoints

    # Reset mock for second test
    mock_client.reset_mock()
    mock_client.assets.get_historical_datapoints.side_effect = [
        jan_datapoints,
        feb_datapoints,
        mar_datapoints,
    ]

    # Test 1 Jan to 1 Apr (should be 3 API calls)
    from_timestamp = JAN_1_2024  # 2024-01-01 00:00:00 UTC
    to_timestamp = APR_1_2024  # 2024-04-01 00:00:00 UTC

    result = mock_openremote_service._get_historical_datapoints(
        "test_asset", "test_attribute", from_timestamp, to_timestamp
    )

    # Should call client method 3 times (Jan 1-31, Feb 1-29, Mar 1-31)
    assert mock_client.assets.get_historical_datapoints.call_count == EXPECTED_CALLS_3_MONTHS

    # Verify boundaries for the second test case
    calls = mock_client.assets.get_historical_datapoints.call_args_list
    first_call_args = calls[0][0]
    last_call_args = calls[2][0]

    # First chunk starts at from_timestamp and last chunk ends at to_timestamp
    assert first_call_args[2] == from_timestamp  # 2024-01-01 00:00:00 UTC
    assert last_call_args[3] == to_timestamp  # 2024-04-01 00:00:00 UTC

    # Check that all datapoints are combined
    expected_datapoints = jan_datapoints + feb_datapoints + mar_datapoints
    assert result == expected_datapoints


def test_get_historical_datapoints_chunking_failure_handling(mock_openremote_service: OpenRemoteService) -> None:
    """Test that chunking fails gracefully when any chunk fails.

    Verifies that:
    - If any chunk request fails (returns None), the entire operation fails
    - The method returns None when any chunk fails
    - Failed requests are logged appropriately
    - The operation stops at the first failure and doesn't continue processing
    """
    # Mock the client method
    mock_client = Mock()
    mock_openremote_service.client = mock_client

    # Mock first chunk succeeds, second chunk fails
    chunk1_datapoints = [AssetDatapoint(x=JAN_1_2024, y=100)]
    mock_client.assets.get_historical_datapoints.side_effect = [
        chunk1_datapoints,
        None,  # Second chunk fails
    ]

    # Test 2 months (Jan 1 to Mar 1)
    from_timestamp = JAN_1_2024  # 2024-01-01 00:00:00 UTC
    to_timestamp = MAR_1_2024  # 2024-03-01 00:00:00 UTC

    result = mock_openremote_service._get_historical_datapoints(
        "test_asset", "test_attribute", from_timestamp, to_timestamp
    )

    # Should return None when any chunk fails
    assert result is None

    # Should call client method 2 times (first succeeds, second fails)
    assert mock_client.assets.get_historical_datapoints.call_count == EXPECTED_CALLS_2_MONTHS


def test_get_historical_datapoints_chunking_edge_case_same_timestamp(
    mock_openremote_service: OpenRemoteService,
) -> None:
    """Test chunking edge case when from_timestamp equals to_timestamp.

    Verifies that:
    - When start and end timestamps are identical, no chunking is applied
    - The request is treated as a single month request (months_diff <= 1)
    - A single API call is made with the identical timestamps
    - The result is returned directly without modification
    """
    # Mock the client method
    mock_client = Mock()
    mock_openremote_service.client = mock_client

    # Mock return value
    mock_datapoints = [AssetDatapoint(x=JAN_1_2024, y=100)]
    mock_client.assets.get_historical_datapoints.return_value = mock_datapoints

    # Test same timestamp
    timestamp = JAN_1_2024  # 2024-01-01 00:00:00 UTC

    result = mock_openremote_service._get_historical_datapoints("test_asset", "test_attribute", timestamp, timestamp)

    # Should call client method once (goes through single month path)
    mock_client.assets.get_historical_datapoints.assert_called_once_with(
        "test_asset", "test_attribute", timestamp, timestamp
    )
    assert result == mock_datapoints
