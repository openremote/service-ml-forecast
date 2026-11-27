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

const fieldLabels: Record<string, string> = {
    forecast_periods: 'Forecasted datapoints',
    forecast_frequency: 'Time between datapoints',
    lags: 'Target history lags',
    lags_past_covariates: 'Past regressor lags',
    lags_future_covariates: 'Future regressor lags',
    output_chunk_length: 'Output chunk length',
    past_count: 'Past count',
    past_period: 'Past period'
};

function displayTerminology(message: string): string {
    return message
        .replace(/covariates/gi, 'regressors')
        .replace(/covariate/gi, 'regressor')
        .replace(/\bWEA\b/g, 'Weighted Exponential Average');
}

export async function responseError(response: Response, fallback: string): Promise<Error> {
    try {
        const payload: unknown = await response.json();
        if (payload && typeof payload === 'object' && 'detail' in payload) {
            const detail = (payload as { detail: unknown }).detail;
            if (typeof detail === 'string' && detail.trim()) return new Error(displayTerminology(detail));
            if (Array.isArray(detail)) {
                const messages = detail
                    .filter(
                        (item): item is { msg: string; loc?: unknown[] } =>
                            !!item && typeof item === 'object' && 'msg' in item && typeof item.msg === 'string'
                    )
                    .map((item) => {
                        const field = (Array.isArray(item.loc) ? [...item.loc].reverse() : []).find(
                            (part): part is string => typeof part === 'string' && Object.prototype.hasOwnProperty.call(fieldLabels, part)
                        );
                        return `${field ? fieldLabels[field] + ': ' : ''}${displayTerminology(item.msg.replace(/^Value error, /, ''))}`;
                    });
                if (messages.length) return new Error([...new Set(messages)].join(' '));
            }
        }
    } catch {
        // Proxies may return an empty or non-JSON response. Keep a useful fallback.
    }
    return new Error(`${fallback} (${response.status})`);
}
