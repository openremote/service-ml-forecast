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

"""Deterministic calendar covariates for historical and future timestamps."""

from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

CALENDAR_COLUMNS = ["calendar_hour_sin", "calendar_hour_cos", "calendar_weekday_sin", "calendar_weekday_cos"]


def add_calendar_regressors(dataframe: pd.DataFrame, timestamp_column: str, timezone: str) -> pd.DataFrame:
    """Add cyclic local hour and weekday values without changing UTC timestamps."""
    local = pd.DatetimeIndex(dataframe[timestamp_column]).tz_localize("UTC").tz_convert(ZoneInfo(timezone))
    hour_angle = 2 * np.pi * local.hour.to_numpy() / 24
    weekday_angle = 2 * np.pi * local.dayofweek.to_numpy() / 7
    result = dataframe.copy()
    result[CALENDAR_COLUMNS[0]] = np.sin(hour_angle)
    result[CALENDAR_COLUMNS[1]] = np.cos(hour_angle)
    result[CALENDAR_COLUMNS[2]] = np.sin(weekday_angle)
    result[CALENDAR_COLUMNS[3]] = np.cos(weekday_angle)
    return result
