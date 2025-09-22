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
import { ModelTypeEnum, ProphetSeasonalityModeEnum, ProphetModelConfig } from '../../services/models';
import { ModelTypeConfig } from './model-registry';
import { DurationInputType, TimeDurationUnit } from '../../components/custom-duration-input';

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
            <or-panel heading="PROPHET PARAMETERS">
                <div class="column">
                    <div class="row">
                        <!-- changepoint_range -->
                        <or-mwc-input
                            type="${InputType.NUMBER}"
                            name="changepoint_range"
                            @or-mwc-input-changed="${handleInput}"
                            label="Changepoint range"
                            .value="${prophetConfig.changepoint_range}"
                            max="1.0"
                            min="0.0"
                            step="0.01"
                            required
                        ></or-mwc-input>

                        <!-- changepoint_prior_scale -->
                        <or-mwc-input
                            type="${InputType.NUMBER}"
                            name="changepoint_prior_scale"
                            @or-mwc-input-changed="${handleInput}"
                            label="Changepoint prior scale"
                            .value="${prophetConfig.changepoint_prior_scale}"
                            max="1.0"
                            min="0.0"
                            step="0.01"
                            required
                        ></or-mwc-input>
                    </div>

                    <div class="row">
                        <!-- seasonality_mode -->
                        <or-mwc-input
                            type="${InputType.SELECT}"
                            .options="${[
                                [ProphetSeasonalityModeEnum.ADDITIVE, 'Additive'],
                                [ProphetSeasonalityModeEnum.MULTIPLICATIVE, 'Multiplicative']
                            ]}"
                            name="seasonality_mode"
                            @or-mwc-input-changed="${handleInput}"
                            label="Seasonality mode"
                            .value="${prophetConfig.seasonality_mode}"
                            required
                        ></or-mwc-input>

                        <!-- daily_seasonality -->
                        <or-mwc-input
                            type="${InputType.CHECKBOX}"
                            name="daily_seasonality"
                            @or-mwc-input-changed="${handleInput}"
                            label="Daily seasonality"
                            .value="${prophetConfig.daily_seasonality}"
                        ></or-mwc-input>

                        <!-- weekly_seasonality -->
                        <or-mwc-input
                            type="${InputType.CHECKBOX}"
                            name="weekly_seasonality"
                            @or-mwc-input-changed="${handleInput}"
                            label="Weekly seasonality"
                            .value="${prophetConfig.weekly_seasonality}"
                        ></or-mwc-input>

                        <!-- yearly_seasonality -->
                        <or-mwc-input
                            type="${InputType.CHECKBOX}"
                            name="yearly_seasonality"
                            @or-mwc-input-changed="${handleInput}"
                            label="Yearly seasonality"
                            .value="${prophetConfig.yearly_seasonality}"
                        ></or-mwc-input>
                    </div>
                </div>
            </or-panel>
        `;
    },

    getCovariatesTemplate: (config, context) => {
        const prophetConfig = config as ProphetModelConfig;

        // Helper functions for Prophet regressor handling
        const handleAddRegressor = () => {
            prophetConfig.regressors = prophetConfig.regressors ?? [];
            prophetConfig.regressors.push({
                asset_id: '',
                attribute_name: '',
                training_data_period: 'P6M'
            });
            context.requestUpdate();
        };

        const handleDeleteRegressor = (index: number) => {
            if (!prophetConfig.regressors) return;
            prophetConfig.regressors.splice(index, 1);
            if (prophetConfig.regressors.length === 0) {
                prophetConfig.regressors = null;
            }
            context.requestUpdate();
        };

        const handleRegressorInput = (ev: OrInputChangedEvent, index: number) => {
            const value = ev.detail?.value;
            const target = ev.target as HTMLInputElement;

            if (!target || value === undefined || !prophetConfig.regressors) {
                return;
            }

            // Auto-select first attribute when asset changes
            if (target.name === 'asset_id') {
                prophetConfig.regressors[index].attribute_name =
                    context.attributeSelectList
                        .get(value as string)
                        ?.values()
                        .next().value ?? '';
            }

            prophetConfig.regressors[index] = {
                ...prophetConfig.regressors[index],
                [target.name]: value
            };
            context.requestUpdate();
        };

        const getRegressorTemplate = (index: number) => {
            if (!prophetConfig.regressors) return html``;

            const regressor = prophetConfig.regressors[index];
            return html`
                <or-panel heading="REGRESSOR ${index + 1}">
                    <div class="column">
                        <div class="row">
                            <or-mwc-input
                                type="${InputType.SELECT}"
                                name="asset_id"
                                @or-mwc-input-changed="${(e: OrInputChangedEvent) => handleRegressorInput(e, index)}"
                                label="Asset"
                                .value="${regressor.asset_id}"
                                .options="${[...context.assetSelectList.entries()]}"
                                .searchProvider="${context.assetSelectList.size > 0 ? context.searchAssets : null}"
                            ></or-mwc-input>

                            ${when(
                                regressor.asset_id,
                                () => html`
                                    <or-mwc-input
                                        type="${InputType.SELECT}"
                                        name="attribute_name"
                                        @or-mwc-input-changed="${(e: OrInputChangedEvent) => handleRegressorInput(e, index)}"
                                        label="Attribute"
                                        .value="${regressor.attribute_name}"
                                        .options="${[...(context.attributeSelectList.get(regressor.asset_id) ?? new Map())]}"
                                    ></or-mwc-input>
                                `,
                                () => html`
                                    <or-mwc-input
                                        type="${InputType.SELECT}"
                                        name="attribute_name"
                                        label="Attribute"
                                        disabled
                                    ></or-mwc-input>
                                `
                            )}

                            <custom-duration-input
                                name="training_data_period"
                                .type="${DurationInputType.ISO_8601}"
                                @value-changed="${(e: OrInputChangedEvent) => handleRegressorInput(e, index)}"
                                label="Training data period"
                                .iso_units="${[TimeDurationUnit.DAY, TimeDurationUnit.WEEK, TimeDurationUnit.MONTH, TimeDurationUnit.YEAR]}"
                                .value="${regressor.training_data_period}"
                            ></custom-duration-input>

                            <or-mwc-input
                                style="max-width: 48px;"
                                type="${InputType.BUTTON}"
                                icon="delete"
                                @click="${() => handleDeleteRegressor(index)}"
                            ></or-mwc-input>
                        </div>
                    </div>
                </or-panel>
            `;
        };

        const getAddRegressorTemplate = () => html`
            <or-panel>
                <div class="row regressor-row">
                    <or-mwc-input
                        type="${InputType.BUTTON}"
                        icon="plus"
                        label="add regressor"
                        @click="${handleAddRegressor}"
                    ></or-mwc-input>
                </div>
            </or-panel>
        `;

        return html`
            ${when(
                prophetConfig.regressors,
                () => map(prophetConfig.regressors ?? [], (_regressor, index) => getRegressorTemplate(index)),
                () => html``
            )}
            ${getAddRegressorTemplate()}
        `;
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
