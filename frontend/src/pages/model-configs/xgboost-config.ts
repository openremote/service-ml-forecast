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
import { map } from 'lit/directives/map.js';
import { when } from 'lit/directives/when.js';
import { InputType, OrInputChangedEvent } from '@openremote/or-mwc-components/or-mwc-input';
import { ModelTypeEnum, XGBoostModelConfig } from '../../services/models';
import { ModelTypeConfig } from './model-registry';
import { DurationInputType, TimeDurationUnit } from '../../components/custom-duration-input';

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
        lags: 1,
        lags_past_covariates: null,
        lags_future_covariates: null,
        output_chunk_length: 1,
        n_estimators: 100,
        max_depth: 6,
        learning_rate: 0.1,
        subsample: 1.0,
        random_state: 42
    } as Partial<XGBoostModelConfig>,
    
    getParametersTemplate: (config, handleInput) => {
        const xgboostConfig = config as XGBoostModelConfig;
        return html`
            <or-panel heading="XGBOOST PARAMETERS">
                <div class="column">
                    <div class="row">
                        <!-- lags -->
                        <or-mwc-input
                            type="${InputType.NUMBER}"
                            name="lags"
                            @or-mwc-input-changed="${handleInput}"
                            label="Lags"
                            .value="${xgboostConfig.lags}"
                            min="1"
                            required
                        ></or-mwc-input>
                        
                        <!-- output_chunk_length -->
                        <or-mwc-input
                            type="${InputType.NUMBER}"
                            name="output_chunk_length"
                            @or-mwc-input-changed="${handleInput}"
                            label="Output chunk length"
                            .value="${xgboostConfig.output_chunk_length}"
                            min="1"
                            required
                        ></or-mwc-input>
                        
                        <!-- n_estimators -->
                        <or-mwc-input
                            type="${InputType.NUMBER}"
                            name="n_estimators"
                            @or-mwc-input-changed="${handleInput}"
                            label="Number of estimators"
                            .value="${xgboostConfig.n_estimators}"
                            min="1"
                            required
                        ></or-mwc-input>
                    </div>
                    
                    <div class="row">
                        <!-- max_depth -->
                        <or-mwc-input
                            type="${InputType.NUMBER}"
                            name="max_depth"
                            @or-mwc-input-changed="${handleInput}"
                            label="Max depth"
                            .value="${xgboostConfig.max_depth}"
                            min="1"
                            required
                        ></or-mwc-input>
                        
                        <!-- learning_rate -->
                        <or-mwc-input
                            type="${InputType.NUMBER}"
                            name="learning_rate"
                            @or-mwc-input-changed="${handleInput}"
                            label="Learning rate"
                            .value="${xgboostConfig.learning_rate}"
                            min="0.001"
                            max="1.0"
                            step="0.001"
                            required
                        ></or-mwc-input>
                        
                        <!-- subsample -->
                        <or-mwc-input
                            type="${InputType.NUMBER}"
                            name="subsample"
                            @or-mwc-input-changed="${handleInput}"
                            label="Subsample"
                            .value="${xgboostConfig.subsample}"
                            min="0.1"
                            max="1.0"
                            step="0.1"
                            required
                        ></or-mwc-input>
                    </div>
                    
                    <div class="row">
                        <!-- random_state -->
                        <or-mwc-input
                            type="${InputType.NUMBER}"
                            name="random_state"
                            @or-mwc-input-changed="${handleInput}"
                            label="Random state"
                            .value="${xgboostConfig.random_state}"
                            min="0"
                        ></or-mwc-input>
                    </div>
                </div>
            </or-panel>
        `;
    },
    
    getCovariatesTemplate: (config, context) => {
        const xgboostConfig = config as XGBoostModelConfig;
        
        // Past Covariates Handlers
        const handleAddPastCovariate = () => {
            xgboostConfig.past_covariates = xgboostConfig.past_covariates ?? [];
            xgboostConfig.past_covariates.push({
                asset_id: '',
                attribute_name: '',
                training_data_period: 'P6M'
            });
            context.requestUpdate();
        };

        const handleDeletePastCovariate = (index: number) => {
            if (!xgboostConfig.past_covariates) return;
            xgboostConfig.past_covariates.splice(index, 1);
            if (xgboostConfig.past_covariates.length === 0) {
                xgboostConfig.past_covariates = null;
            }
            context.requestUpdate();
        };

        const handlePastCovariateInput = (ev: OrInputChangedEvent, index: number) => {
            const value = ev.detail?.value;
            const target = ev.target as HTMLInputElement;

            if (!target || value === undefined || !xgboostConfig.past_covariates) return;

            if (target.name === 'asset_id') {
                xgboostConfig.past_covariates[index].attribute_name =
                    context.attributeSelectList.get(value as string)?.values().next().value ?? '';
            }

            xgboostConfig.past_covariates[index] = {
                ...xgboostConfig.past_covariates[index],
                [target.name]: value
            };
            context.requestUpdate();
        };

        // Future Covariates Handlers
        const handleAddFutureCovariate = () => {
            xgboostConfig.future_covariates = xgboostConfig.future_covariates ?? [];
            xgboostConfig.future_covariates.push({
                asset_id: '',
                attribute_name: '',
                training_data_period: 'P6M'
            });
            context.requestUpdate();
        };

        const handleDeleteFutureCovariate = (index: number) => {
            if (!xgboostConfig.future_covariates) return;
            xgboostConfig.future_covariates.splice(index, 1);
            if (xgboostConfig.future_covariates.length === 0) {
                xgboostConfig.future_covariates = null;
            }
            context.requestUpdate();
        };

        const handleFutureCovariateInput = (ev: OrInputChangedEvent, index: number) => {
            const value = ev.detail?.value;
            const target = ev.target as HTMLInputElement;

            if (!target || value === undefined || !xgboostConfig.future_covariates) return;

            if (target.name === 'asset_id') {
                xgboostConfig.future_covariates[index].attribute_name =
                    context.attributeSelectList.get(value as string)?.values().next().value ?? '';
            }

            xgboostConfig.future_covariates[index] = {
                ...xgboostConfig.future_covariates[index],
                [target.name]: value
            };
            context.requestUpdate();
        };

        // Template Generators
        const getPastCovariateTemplate = (index: number) => {
            if (!xgboostConfig.past_covariates) return html``;
            
            const covariate = xgboostConfig.past_covariates[index];
            return html`
                <or-panel heading="PAST COVARIATE ${index + 1}">
                    <div class="column">
                        <div class="row">
                            <or-mwc-input
                                type="${InputType.SELECT}"
                                name="asset_id"
                                @or-mwc-input-changed="${(e: OrInputChangedEvent) => handlePastCovariateInput(e, index)}"
                                label="Asset"
                                .value="${covariate.asset_id}"
                                .options="${[...context.assetSelectList.entries()]}"
                                .searchProvider="${context.assetSelectList.size > 0 ? context.searchAssets : null}"
                            ></or-mwc-input>

                            ${when(
                                covariate.asset_id,
                                () => html`
                                    <or-mwc-input
                                        type="${InputType.SELECT}"
                                        name="attribute_name"
                                        @or-mwc-input-changed="${(e: OrInputChangedEvent) => handlePastCovariateInput(e, index)}"
                                        label="Attribute"
                                        .value="${covariate.attribute_name}"
                                        .options="${[...(context.attributeSelectList.get(covariate.asset_id) ?? new Map())]}"
                                    ></or-mwc-input>
                                `,
                                () => html`
                                    <or-mwc-input type="${InputType.SELECT}" name="attribute_name" label="Attribute" disabled></or-mwc-input>
                                `
                            )}

                            <custom-duration-input
                                name="training_data_period"
                                .type="${DurationInputType.ISO_8601}"
                                @value-changed="${(e: OrInputChangedEvent) => handlePastCovariateInput(e, index)}"
                                label="Training data period"
                                .iso_units="${[TimeDurationUnit.DAY, TimeDurationUnit.WEEK, TimeDurationUnit.MONTH, TimeDurationUnit.YEAR]}"
                                .value="${covariate.training_data_period}"
                            ></custom-duration-input>

                            <or-mwc-input
                                style="max-width: 48px;"
                                type="${InputType.BUTTON}"
                                icon="delete"
                                @click="${() => handleDeletePastCovariate(index)}"
                            ></or-mwc-input>
                        </div>
                    </div>
                </or-panel>
            `;
        };

        const getFutureCovariateTemplate = (index: number) => {
            if (!xgboostConfig.future_covariates) return html``;
            
            const covariate = xgboostConfig.future_covariates[index];
            return html`
                <or-panel heading="FUTURE COVARIATE ${index + 1}">
                    <div class="column">
                        <div class="row">
                            <or-mwc-input
                                type="${InputType.SELECT}"
                                name="asset_id"
                                @or-mwc-input-changed="${(e: OrInputChangedEvent) => handleFutureCovariateInput(e, index)}"
                                label="Asset"
                                .value="${covariate.asset_id}"
                                .options="${[...context.assetSelectList.entries()]}"
                                .searchProvider="${context.assetSelectList.size > 0 ? context.searchAssets : null}"
                            ></or-mwc-input>

                            ${when(
                                covariate.asset_id,
                                () => html`
                                    <or-mwc-input
                                        type="${InputType.SELECT}"
                                        name="attribute_name"
                                        @or-mwc-input-changed="${(e: OrInputChangedEvent) => handleFutureCovariateInput(e, index)}"
                                        label="Attribute"
                                        .value="${covariate.attribute_name}"
                                        .options="${[...(context.attributeSelectList.get(covariate.asset_id) ?? new Map())]}"
                                    ></or-mwc-input>
                                `,
                                () => html`
                                    <or-mwc-input type="${InputType.SELECT}" name="attribute_name" label="Attribute" disabled></or-mwc-input>
                                `
                            )}

                            <custom-duration-input
                                name="training_data_period"
                                .type="${DurationInputType.ISO_8601}"
                                @value-changed="${(e: OrInputChangedEvent) => handleFutureCovariateInput(e, index)}"
                                label="Training data period"
                                .iso_units="${[TimeDurationUnit.DAY, TimeDurationUnit.WEEK, TimeDurationUnit.MONTH, TimeDurationUnit.YEAR]}"
                                .value="${covariate.training_data_period}"
                            ></custom-duration-input>

                            <or-mwc-input
                                style="max-width: 48px;"
                                type="${InputType.BUTTON}"
                                icon="delete"
                                @click="${() => handleDeleteFutureCovariate(index)}"
                            ></or-mwc-input>
                        </div>
                    </div>
                </or-panel>
            `;
        };

        const getAddPastCovariateTemplate = () => html`
            <or-panel>
                <div class="row regressor-row">
                    <or-mwc-input
                        type="${InputType.BUTTON}"
                        icon="plus"
                        label="add past covariate"
                        @click="${handleAddPastCovariate}"
                    ></or-mwc-input>
                </div>
            </or-panel>
        `;

        const getAddFutureCovariateTemplate = () => html`
            <or-panel>
                <div class="row regressor-row">
                    <or-mwc-input
                        type="${InputType.BUTTON}"
                        icon="plus"
                        label="add future covariate"
                        @click="${handleAddFutureCovariate}"
                    ></or-mwc-input>
                </div>
            </or-panel>
        `;

        return html`
            ${when(
                xgboostConfig.past_covariates,
                () => map(xgboostConfig.past_covariates ?? [], (_covariate, index) => getPastCovariateTemplate(index)),
                () => html``
            )}
            ${getAddPastCovariateTemplate()}
            
            ${when(
                xgboostConfig.future_covariates,
                () => map(xgboostConfig.future_covariates ?? [], (_covariate, index) => getFutureCovariateTemplate(index)),
                () => html``
            )}
            ${getAddFutureCovariateTemplate()}
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
