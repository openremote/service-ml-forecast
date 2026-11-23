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
import { keyed } from 'lit/directives/keyed.js';
import '@openremote/or-vaadin-components/or-vaadin-number-field';
import { ModelTypeEnum, XGBoostModelConfig } from '../../services/models';
import { ModelTypeConfig } from './model-registry';
import { assetInputs } from './asset-inputs';

/**
 * XGBoost model configuration for the model registry.
 * Defines the UI, validation, and default values for XGBoost models.
 */
export const XGBoostConfig: ModelTypeConfig = {
    label: 'XGBoost',

    defaultConfig: {
        type: ModelTypeEnum.XGBOOST,
        past_covariates: null,
        future_covariates: null,
        lags: 168,
        lags_past_covariates: null,
        lags_future_covariates: null,
        output_chunk_length: 1,
        n_estimators: 100,
        max_depth: 6,
        learning_rate: 0.1,
        subsample: 0.8,
        random_state: 42
    } as Partial<XGBoostModelConfig>,

    getParametersTemplate: (config, handleInput) => {
        const xgboostConfig = config as XGBoostModelConfig;
        return html`
            <details class="config-group" open>
                <summary>Tree model parameters</summary>
                <div class="group-content">
                    <div class="column">
                        ${keyed(
                            config.type,
                            html`<covariate-lags-input
                                name="lags"
                                label="Target history lags (steps)"
                                .role=${'past'}
                                .value=${xgboostConfig.lags}
                                @value-changed=${handleInput}
                            ></covariate-lags-input>`
                        )}
                        <div class="row">
                            <or-vaadin-number-field
                                name="output_chunk_length"
                                @input="${handleInput}"
                                label="Output chunk length"
                                .value=${Number.isFinite(xgboostConfig.output_chunk_length)
                                    ? String(xgboostConfig.output_chunk_length)
                                    : ''}
                                step="1"
                                min="1"
                                error-message="Enter a whole number of at least 1."
                                required
                            ></or-vaadin-number-field>

                            <or-vaadin-number-field
                                name="n_estimators"
                                @input="${handleInput}"
                                label="Number of estimators"
                                .value=${Number.isFinite(xgboostConfig.n_estimators) ? String(xgboostConfig.n_estimators) : ''}
                                step="1"
                                min="1"
                                error-message="Enter a whole number of at least 1."
                                required
                            ></or-vaadin-number-field>
                        </div>

                        <div class="row">
                            <or-vaadin-number-field
                                name="max_depth"
                                @input="${handleInput}"
                                label="Max depth"
                                .value=${Number.isFinite(xgboostConfig.max_depth) ? String(xgboostConfig.max_depth) : ''}
                                step="1"
                                min="1"
                                error-message="Enter a whole number of at least 1."
                                required
                            ></or-vaadin-number-field>

                            <or-vaadin-number-field
                                name="learning_rate"
                                @input="${handleInput}"
                                label="Learning rate"
                                .value=${Number.isFinite(xgboostConfig.learning_rate) ? String(xgboostConfig.learning_rate) : ''}
                                min="0.001"
                                max="1.0"
                                step="0.001"
                                error-message="Enter a value from 0.001 to 1 in steps of 0.001."
                                required
                            ></or-vaadin-number-field>

                            <or-vaadin-number-field
                                name="subsample"
                                @input="${handleInput}"
                                label="Subsample"
                                .value=${Number.isFinite(xgboostConfig.subsample) ? String(xgboostConfig.subsample) : ''}
                                min="0.1"
                                max="1.0"
                                step="0.1"
                                error-message="Enter a value from 0.1 to 1 in steps of 0.1."
                                required
                            ></or-vaadin-number-field>
                        </div>

                        <div class="row">
                            <or-vaadin-number-field
                                name="random_state"
                                @input="${handleInput}"
                                label="Random state"
                                .value=${Number.isFinite(xgboostConfig.random_state) ? String(xgboostConfig.random_state) : ''}
                                step="1"
                                min="0"
                                error-message="Enter a whole number of at least 0."
                                required
                            ></or-vaadin-number-field>
                        </div>
                    </div>
                </div>
            </details>
        `;
    },

    getCovariatesTemplate: (config, context) => {
        const tree = config as XGBoostModelConfig;
        return html`
            ${assetInputs({
                title: 'Future regressors',
                role: 'future',
                context,
                description:
                    'Optional regressors with historical data and future values available when the forecast is made, such as weather forecasts or known schedules.',
                features: tree.future_covariates,
                lags: tree.lags_future_covariates,
                onLags: (value) => {
                    tree.lags_future_covariates = value;
                },
                onChange: (features) => {
                    tree.future_covariates = features;
                    if (!features?.length) tree.lags_future_covariates = null;
                    if (features?.length && tree.lags_future_covariates == null) tree.lags_future_covariates = [0];
                }
            })}
            ${assetInputs({
                title: 'Past regressors',
                role: 'past',
                context,
                description: 'Optional observed inputs. The selected lags must provide enough history for the full forecast.',
                features: tree.past_covariates,
                lags: tree.lags_past_covariates,
                onLags: (value) => {
                    tree.lags_past_covariates = value;
                },
                onChange: (features) => {
                    tree.past_covariates = features;
                    if (!features?.length) tree.lags_past_covariates = null;
                    if (features?.length && tree.lags_past_covariates == null) tree.lags_past_covariates = [-tree.forecast_periods];
                }
            })}
        `;
    },

    validateConfig: (config) => {
        const xgboostConfig = config as XGBoostModelConfig;

        // Validate past covariates
        if (xgboostConfig.past_covariates) {
            for (const covariate of xgboostConfig.past_covariates) {
                if (!covariate.asset_id || !covariate.attribute_name) {
                    return false;
                }
            }
        }

        // Validate future covariates
        if (xgboostConfig.future_covariates) {
            for (const covariate of xgboostConfig.future_covariates) {
                if (!covariate.asset_id || !covariate.attribute_name) {
                    return false;
                }
            }
        }

        return true;
    }
};
