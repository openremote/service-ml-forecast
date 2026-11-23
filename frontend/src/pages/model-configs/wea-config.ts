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

import { html } from 'lit';
import '@openremote/or-vaadin-components/or-vaadin-number-field';
import { DurationInputType, TimeDurationUnit } from '../../components/custom-duration-input';
import { ModelTypeEnum, type WEAModelConfig } from '../../services/models';
import type { ModelTypeConfig } from './model-registry';
import { weaValidationMessage } from './wea-validation';

export const WEAConfig: ModelTypeConfig = {
    label: 'Weighted Exponential Average',
    defaultConfig: { type: ModelTypeEnum.WEA, past_period: 'P7D', past_count: 4, calendar_timezone: null },
    getParametersTemplate: (config, handleInput) => {
        const wea = config as WEAModelConfig;
        return html`<details class="config-group" open>
            <summary>Weighted Exponential Average parameters</summary>
            <div class="group-content">
                <div class="column">
                    <div class="row">
                        <custom-duration-input
                            name="past_period"
                            label="Past period"
                            .type=${DurationInputType.ISO_8601}
                            .iso_units=${[TimeDurationUnit.HOUR, TimeDurationUnit.DAY, TimeDurationUnit.WEEK]}
                            .value=${wea.past_period}
                            @value-changed=${handleInput}
                        ></custom-duration-input>
                        <or-vaadin-number-field
                            name="past_count"
                            label="Past count"
                            .value=${Number.isFinite(wea.past_count) ? String(wea.past_count) : ''}
                            min="1"
                            max="100"
                            step="1"
                            error-message="Enter a whole number from 1 to 100."
                            required
                            @input=${handleInput}
                        ></or-vaadin-number-field>
                    </div>
                    ${weaValidationMessage(wea)
                        ? html`<p class="input-help" role="alert">${weaValidationMessage(wea)}</p>`
                        : html`<p class="input-help">
                              Weighted Exponential Average of target history. The forecast horizon must fit within the past period.
                          </p>`}
                </div>
            </div>
        </details>`;
    },
    getCovariatesTemplate: () => html``,
    validateConfig: (config) => {
        const wea = config as WEAModelConfig;
        return weaValidationMessage(wea) === null;
    }
};
