# Copyright 2026, OpenRemote Inc.
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

"""Guard UTC instants that legacy Manager wall-time storage cannot distinguish."""

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from service_ml_forecast.common.exceptions import ResourceValidationError

HOUR_MS = 3_600_000
DAY_MS = 24 * HOUR_MS


def require_unambiguous_window(first_ms: int, last_ms: int, timezone_name: str) -> None:
    """Reject any overlap with either occurrence of a backward clock interval.

    Bounds are inclusive. Inspect transitions beyond the requested bounds too:
    the first occurrence precedes the actual offset change. UTC transports do
    not require this legacy-storage restriction. This does not repair old data.
    """
    if last_ms < first_ms:
        raise ResourceValidationError("Datapoint UTC window is reversed")
    zone = ZoneInfo(timezone_name)
    if timezone_name in {"UTC", "Etc/UTC", "GMT", "Etc/GMT"}:
        return

    def offset(ms: int) -> timedelta:
        result = datetime.fromtimestamp(ms / 1000, UTC).astimezone(zone).utcoffset()
        assert result is not None
        return result

    cursor = first_ms // HOUR_MS * HOUR_MS - DAY_MS
    stop = last_ms + DAY_MS
    previous = offset(cursor)
    while cursor < stop:
        following = cursor + HOUR_MS
        current = offset(following)
        if current < previous:
            low, high = cursor, following
            while high - low > 1:
                middle = (low + high) // 2
                if offset(middle) == previous:
                    low = middle
                else:
                    high = middle
            repeated_ms = int((previous - current).total_seconds() * 1000)
            if first_ms < high + repeated_ms and last_ms >= high - repeated_ms:
                raise ResourceValidationError(
                    f"Manager datapoint window includes ambiguous local time in {timezone_name}; "
                    "both repeated clock hours require verified UTC-preserving storage/source data"
                )
        cursor, previous = following, current
