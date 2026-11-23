// Copyright 2025, OpenRemote Inc.
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
import { guard } from 'lit/directives/guard.js';
import '@openremote/or-vaadin-components/or-vaadin-number-field';
import '@openremote/or-vaadin-components/or-vaadin-select';
import '@openremote/or-vaadin-components/or-vaadin-checkbox';
import { ModelTypeEnum, ProphetSeasonalityModeEnum, ProphetModelConfig } from '../../services/models';
import { ModelTypeConfig } from './model-registry';
import { assetInputs } from './asset-inputs';

/**
 * Prophet model configuration for the model registry.
 * Defines the UI, validation, and default values for Prophet models.
 */
export const ProphetConfig: ModelTypeConfig = {
    label: 'Prophet',

    defaultConfig: {
        type: ModelTypeEnum.PROPHET,
        regressors: null,
        daily_seasonality: true,
        weekly_seasonality: true,
        yearly_seasonality: true,
        changepoint_range: 0.8,
        changepoint_prior_scale: 0.05,
        seasonality_mode: ProphetSeasonalityModeEnum.ADDITIVE
    } as Partial<ProphetModelConfig>,

    getParametersTemplate: (config, handleInput) => {
        const prophetConfig = config as ProphetModelConfig;
        return html`
            <details class="config-group" open>
                <summary>Prophet parameters</summary>
                <div class="group-content">
                    <div class="column">
                        <div class="row">
                            <or-vaadin-number-field
                                name="changepoint_range"
                                @input="${handleInput}"
                                label="Changepoint range"
                                .value=${Number.isFinite(prophetConfig.changepoint_range) ? String(prophetConfig.changepoint_range) : ''}
                                max="1.0"
                                min="0.0"
                                step="0.01"
                                error-message="Enter a value from 0 to 1 in steps of 0.01."
                                required
                            ></or-vaadin-number-field>

                            <or-vaadin-number-field
                                name="changepoint_prior_scale"
                                @input="${handleInput}"
                                label="Changepoint prior scale"
                                .value=${Number.isFinite(prophetConfig.changepoint_prior_scale)
                                    ? String(prophetConfig.changepoint_prior_scale)
                                    : ''}
                                max="1.0"
                                min="0.0"
                                step="0.01"
                                error-message="Enter a value from 0 to 1 in steps of 0.01."
                                required
                            ></or-vaadin-number-field>
                        </div>

                        <div class="row">
                            <or-vaadin-select
                                .items=${guard([], () => [
                                    { value: ProphetSeasonalityModeEnum.ADDITIVE, label: 'Additive' },
                                    { value: ProphetSeasonalityModeEnum.MULTIPLICATIVE, label: 'Multiplicative' }
                                ])}
                                name="seasonality_mode"
                                @change="${handleInput}"
                                label="Seasonality mode"
                                .value="${prophetConfig.seasonality_mode}"
                                required
                            ></or-vaadin-select>

                            <or-vaadin-checkbox
                                name="daily_seasonality"
                                @change="${handleInput}"
                                label="Daily seasonality"
                                .checked="${prophetConfig.daily_seasonality}"
                            ></or-vaadin-checkbox>

                            <or-vaadin-checkbox
                                name="weekly_seasonality"
                                @change="${handleInput}"
                                label="Weekly seasonality"
                                .checked="${prophetConfig.weekly_seasonality}"
                            ></or-vaadin-checkbox>

                            <or-vaadin-checkbox
                                name="yearly_seasonality"
                                @change="${handleInput}"
                                label="Yearly seasonality"
                                .checked="${prophetConfig.yearly_seasonality}"
                            ></or-vaadin-checkbox>
                        </div>
                    </div>
                </div>
            </details>
        `;
    },

    getCovariatesTemplate: (config, context) => {
        const prophet = config as ProphetModelConfig;
        return assetInputs({
            title: 'Regressors',
            role: 'future',
            context,
            description:
                'Optional regressors with historical data and future values available when the forecast is made, such as weather forecasts or known schedules.',
            features: prophet.regressors,
            onChange: (features) => {
                prophet.regressors = features;
            }
        });
    },

    validateConfig: (config) => {
        const prophetConfig = config as ProphetModelConfig;
        if (prophetConfig.regressors) {
            for (const regressor of prophetConfig.regressors) {
                if (!regressor.asset_id || !regressor.attribute_name) {
                    return false;
                }
            }
        }
        return true;
    }
};
