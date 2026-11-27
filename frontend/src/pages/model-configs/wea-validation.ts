// Copyright 2026, OpenRemote Inc.
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as
// published by the Free Software Foundation, either version 3 of the
// License, or (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
// GNU Affero General Public License for more details.
//
// You should have received a copy of the GNU Affero General Public License
// along with this program. If not, see <https://www.gnu.org/licenses/>.
//
// SPDX-License-Identifier: AGPL-3.0-or-later

interface WEAWindow {
    past_period: string;
    past_count: number;
    forecast_frequency: string;
    forecast_periods: number;
}

export function weaValidationMessage(config: WEAWindow): string | null {
    if (!Number.isInteger(config.past_count) || config.past_count < 1 || config.past_count > 100) {
        return 'Past count must be a whole number between 1 and 100.';
    }
    const duration =
        /^P(?:(\d+(?:\.\d+)?)W)?(?:(\d+(?:\.\d+)?)D)?(?:T(?:(\d+(?:\.\d+)?)H)?(?:(\d+(?:\.\d+)?)M)?(?:(\d+(?:\.\d+)?)S)?)?$/.exec(
            config.past_period
        );
    const periodMs = duration
        ? duration.slice(1).reduce((sum, value, index) => sum + Number(value || 0) * [604800000, 86400000, 3600000, 60000, 1000][index], 0)
        : 0;
    if (!Number.isSafeInteger(periodMs) || periodMs <= 0) {
        return 'Past period must be a positive fixed duration, such as 7 days. Months and years are not supported.';
    }
    const frequency = /^(\d+(?:\.\d+)?)?(ms|s|min|h|H|D|d)$/.exec(config.forecast_frequency);
    const multipliers: Record<string, number> = { ms: 1, s: 1000, min: 60000, h: 3600000, H: 3600000, D: 86400000, d: 86400000 };
    const stepMs = frequency ? Number(frequency[1] || 1) * multipliers[frequency[2]] : 0;
    if (!Number.isSafeInteger(stepMs) || stepMs <= 0) return 'Time between datapoints must be a positive fixed duration.';
    if (!Number.isSafeInteger(config.forecast_periods) || config.forecast_periods < 1) {
        return 'Forecasted datapoints must be a positive whole number.';
    }
    if (config.forecast_periods * stepMs > periodMs) {
        return 'The forecast horizon must fit within the past period. Reduce forecasted datapoints or increase the past period.';
    }
    return null;
}
