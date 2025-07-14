# Copyright 2025, OpenRemote Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
import time
from datetime import timedelta

import pandas as pd
from isodate import Duration, parse_duration

logger = logging.getLogger(__name__)


class TimeUtil:
    """Utility class for time operations."""

    @staticmethod
    def get_timestamp_ms() -> int:
        """Get the current timestamp in milliseconds."""

        timestamp = int(time.time())
        millis = TimeUtil.sec_to_ms(timestamp)
        return millis

    @staticmethod
    def get_timestamp_sec() -> int:
        """Get the current timestamp in seconds."""
        timestamp = int(time.time())
        return timestamp

    @staticmethod
    def parse_iso_duration(duration: str) -> int:
        """Parse the given time duration String and returns the corresponding number of seconds.

        Args:
            duration: The time duration to parse. (ISO 8601)

        Returns:
            The number of seconds.
        """
        # Parse the ISO 8601 duration string to a timedelta object
        parsed: timedelta | Duration = parse_duration(duration)

        seconds = 0

        # Handle ISO 8601 strings that do not contain MONTH or YEAR (Timedelta)
        if isinstance(parsed, timedelta):
            seconds = int(parsed.total_seconds())

        # Edge case, the library returns a Duration object for ISO 8601 strings that contain MONTH or YEAR
        # So we need to handle the conversion to seconds manually
        if isinstance(parsed, Duration):
            seconds = int(parsed.months * 30 * 24 * 60 * 60)
            seconds += int(parsed.years * 365 * 24 * 60 * 60)  # Not taking into account leap years is OK
            seconds += int(parsed.total_seconds())

        return seconds

    @staticmethod
    def pd_future_timestamp(periods: int, frequency: str) -> int:
        """Get the future timestamp based on the number of periods and frequency.

        Args:
            periods: The number of periods.
            frequency: The frequency. (Pandas frequency string)

        Returns:
            The future timestamp in milliseconds.
        """
        future_time = pd.Timestamp.now() + periods * pd.tseries.frequencies.to_offset(frequency)
        timestamp = int(future_time.timestamp())
        millis = TimeUtil.sec_to_ms(timestamp)

        return millis

    @staticmethod
    def get_period_start_timestamp(period: str) -> int:
        """Get the start timestamp for the period based on the provided ISO 8601 duration string.

        Args:
            period: The ISO 8601 duration string.

        Returns:
            The start timestamp in seconds.
        """
        start_timestamp = TimeUtil.get_timestamp_sec() - TimeUtil.parse_iso_duration(period)
        return start_timestamp

    @staticmethod
    def get_period_start_timestamp_ms(period: str) -> int:
        """Get the start timestamp for the period based on the provided ISO 8601 duration string.

        Args:
            period: The ISO 8601 duration string.

        Returns:
        """
        start_timestamp = TimeUtil.get_period_start_timestamp(period)
        return TimeUtil.sec_to_ms(start_timestamp)

    @staticmethod
    def sec_to_ms(timestamp: int) -> int:
        """Convert the epoch timestamp in seconds to milliseconds.

        Args:
            timestamp: The epoch timestamp in seconds.

        Returns:
            The epoch timestamp in milliseconds. (last 3 digits will be 000)
        """
        return int(timestamp * 1000)

    @staticmethod
    def months_between_timestamps(from_timestamp_ms: int, to_timestamp_ms: int) -> int:
        """Calculate the number of months between two epoch millisecond timestamps.

        Args:
            from_timestamp_ms: The start timestamp in milliseconds.
            to_timestamp_ms: The end timestamp in milliseconds.

        Returns:
            The number of months between the timestamps.
        """
        # Convert milliseconds to pandas timestamps
        from_dt = pd.to_datetime(from_timestamp_ms, unit="ms")
        to_dt = pd.to_datetime(to_timestamp_ms, unit="ms")

        # Calculate the difference in months
        months_diff = (to_dt.year - from_dt.year) * 12 + (to_dt.month - from_dt.month)
        return months_diff

    @staticmethod
    def add_months_to_timestamp(timestamp_ms: int, months: int) -> int:
        """Add a specified number of months to a timestamp in milliseconds.

        Args:
            timestamp_ms: The timestamp in milliseconds.
            months: The number of months to add.

        Returns:
            The new timestamp in milliseconds.
        """
        # Convert milliseconds to pandas timestamp
        dt = pd.to_datetime(timestamp_ms, unit="ms")

        # Add months
        new_dt = dt + pd.DateOffset(months=months)

        # Convert back to milliseconds
        return int(new_dt.timestamp() * 1000)
