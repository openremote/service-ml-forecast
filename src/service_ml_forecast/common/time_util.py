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
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
import time

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
    def parse_iso_duration(duration: str) -> int:
        """Parse the given time duration String and returns the corresponding number of seconds.

        Args:
            duration: The time duration to parse. (ISO 8601)

        Returns:
            The number of seconds.
        """
        # Parse the ISO 8601 duration string to a timedelta object
        duration_obj: Duration = parse_duration(duration, as_timedelta_if_possible=False)

        # Convert the duration object to seconds
        duration_seconds = int(duration_obj.total_seconds())
        return duration_seconds

    @staticmethod
    def pd_future_timestamp(periods: int, frequency: str) -> int:
        """Get the future timestamp based on the number of periods and frequency.

        Args:
            periods: The number of periods.
            frequency: The frequency. (Pandas offset string)

        Returns:
            The future timestamp in milliseconds.
        """
        future_time = pd.Timestamp.now() + periods * pd.tseries.frequencies.to_offset(frequency)
        timestamp = int(future_time.timestamp())
        millis = TimeUtil.sec_to_ms(timestamp)

        return millis

    @staticmethod
    def sec_to_ms(timestamp: int) -> int:
        """Convert the epoch timestamp in seconds to milliseconds.

        Args:
            timestamp: The epoch timestamp in seconds.

        Returns:
            The epoch timestamp in milliseconds. (last 3 digits will be 000)
        """
        return int(timestamp * 1000)
