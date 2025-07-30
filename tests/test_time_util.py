import pytest

from service_ml_forecast.common.time_util import TimeUtil

# Constants for test values
SECONDS_PER_DAY = 86400
SECONDS_PER_MONTH = 2592000  # 30 days
SECONDS_PER_YEAR = 31536000  # 365 days
MILLISECONDS_PER_SECOND = 1000
EXPECTED_MONTHS_1 = 1
EXPECTED_MONTHS_2 = 2


class TestTimeUtil:
    """Test cases for TimeUtil class focusing on core functionality and edge cases."""

    def test_months_between_timestamps(self) -> None:
        """Test month calculation with key scenarios.

        Verifies that:
        - Basic month differences are calculated correctly (Jan to Feb = 1 month)
        - Multi-month differences work (Jan to Mar = 2 months)
        - Year boundary transitions work correctly (Dec to Jan = 1 month)
        - Same timestamp returns 0 months
        - Reverse timestamps return negative values
        """
        jan_1_2024 = 1704067200000  # 2024-01-01 00:00:00 UTC
        feb_1_2024 = 1706745600000  # 2024-02-01 00:00:00 UTC
        mar_1_2024 = 1709251200000  # 2024-03-01 00:00:00 UTC
        dec_1_2023 = 1701388800000  # 2023-12-01 00:00:00 UTC

        # Basic scenarios
        assert TimeUtil.months_between_timestamps(jan_1_2024, feb_1_2024) == EXPECTED_MONTHS_1
        assert TimeUtil.months_between_timestamps(jan_1_2024, mar_1_2024) == EXPECTED_MONTHS_2
        assert TimeUtil.months_between_timestamps(dec_1_2023, jan_1_2024) == EXPECTED_MONTHS_1

        # Edge cases
        assert TimeUtil.months_between_timestamps(jan_1_2024, jan_1_2024) == 0
        assert TimeUtil.months_between_timestamps(feb_1_2024, jan_1_2024) == -1

    def test_add_months_to_timestamp(self) -> None:
        """Test month addition with key scenarios.

        Verifies that:
        - Adding 1 month to Jan 1 results in Feb 1
        - Adding 2 months to Jan 1 results in Mar 1
        - Year boundary transitions work (Dec + 1 = Jan)
        - Adding 0 months returns the original timestamp
        - Adding negative months works correctly
        """
        jan_1_2024 = 1704067200000  # 2024-01-01 00:00:00 UTC
        feb_1_2024 = 1706745600000  # 2024-02-01 00:00:00 UTC
        mar_1_2024 = 1709251200000  # 2024-03-01 00:00:00 UTC
        dec_1_2023 = 1701388800000  # 2023-12-01 00:00:00 UTC

        # Basic scenarios
        assert TimeUtil.add_months_to_timestamp(jan_1_2024, 1) == feb_1_2024
        assert TimeUtil.add_months_to_timestamp(jan_1_2024, 2) == mar_1_2024
        assert TimeUtil.add_months_to_timestamp(dec_1_2023, 1) == jan_1_2024

        # Edge cases
        assert TimeUtil.add_months_to_timestamp(jan_1_2024, 0) == jan_1_2024
        assert TimeUtil.add_months_to_timestamp(jan_1_2024, -1) == dec_1_2023

    def test_parse_iso_duration(self) -> None:
        """Test ISO duration parsing with key scenarios.

        Verifies that:
        - Complex ISO 8601 durations with all components are parsed correctly
        - Simple year durations work (P10Y = 10 years)
        - Zero duration returns 0 seconds
        - All time components (Y, M, D, H, M, S) are handled properly
        """
        # Complex duration
        expected_complex = (
            SECONDS_PER_YEAR  # 1Y
            + 6 * SECONDS_PER_MONTH  # 6M
            + 15 * SECONDS_PER_DAY  # 15D
            + 12 * 3600  # 12H
            + 30 * 60  # 30M
            + 45  # 45S
        )
        assert TimeUtil.parse_iso_duration("P1Y6M15DT12H30M45S") == expected_complex

        # Simple durations
        assert TimeUtil.parse_iso_duration("P10Y") == 10 * SECONDS_PER_YEAR
        assert TimeUtil.parse_iso_duration("P0D") == 0

    def test_get_period_start_timestamp_ms(self) -> None:
        """Test period start timestamp calculation.

        Verifies that:
        - The current time minus the parsed duration equals the start timestamp
        - The result is correctly converted to milliseconds
        - The calculation works with ISO 8601 duration strings
        """
        with pytest.MonkeyPatch().context() as m:
            fixed_time = 1710504000  # 2024-03-15 12:00:00 UTC in seconds
            m.setattr(TimeUtil, "get_timestamp_sec", lambda: fixed_time)

            result = TimeUtil.get_period_start_timestamp_ms("P3M")
            expected = (fixed_time - 3 * SECONDS_PER_MONTH) * MILLISECONDS_PER_SECOND
            assert result == expected

    def test_pd_future_timestamp(self) -> None:
        """Test future timestamp calculation.

        Verifies that:
        - Adding periods to the current time results in a future timestamp
        - The result is greater than the current timestamp
        - Pandas frequency strings are handled correctly
        """
        with pytest.MonkeyPatch().context() as m:
            fixed_time = 1710504000  # 2024-03-15 12:00:00 UTC in seconds
            m.setattr(TimeUtil, "get_timestamp_sec", lambda: fixed_time)

            result = TimeUtil.pd_future_timestamp(1, "D")
            current_ms = fixed_time * MILLISECONDS_PER_SECOND
            assert result > current_ms

    def test_invalid_iso_duration_handling(self) -> None:
        """Test handling of invalid ISO duration strings.

        Verifies that:
        - Invalid duration strings raise ValueError
        - Empty strings raise ValueError
        - None values raise TypeError
        - The method fails gracefully with proper error types
        """
        with pytest.raises(ValueError):
            TimeUtil.parse_iso_duration("invalid")

        with pytest.raises(ValueError):
            TimeUtil.parse_iso_duration("")

        with pytest.raises(TypeError):
            TimeUtil.parse_iso_duration(None)

    def test_timestamp_edge_cases(self) -> None:
        """Test timestamp methods with extreme edge cases.

        Verifies that:
        - Very old dates (epoch start) work correctly
        - Very large timestamps are handled properly
        - Zero timestamps work correctly
        - The sec_to_ms conversion works for all valid inputs
        """
        # Test with very old dates
        old_timestamp = 0  # 1970-01-01
        recent_timestamp = 1704067200000  # 2024-01-01
        months_diff = TimeUtil.months_between_timestamps(old_timestamp, recent_timestamp)
        assert months_diff > 0

        # Test with very large timestamps
        large_timestamp = 9999999999999
        assert TimeUtil.sec_to_ms(large_timestamp) == large_timestamp * MILLISECONDS_PER_SECOND
        assert TimeUtil.sec_to_ms(0) == 0
