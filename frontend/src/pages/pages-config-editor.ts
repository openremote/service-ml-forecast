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

import { css, html, LitElement, PropertyValues } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { map } from 'lit/directives/map.js';
import { when } from 'lit/directives/when.js';
import { ModelTypeEnum, ProphetSeasonalityModeEnum } from '../services/models';
import type { ModelConfig, ProphetModelConfig, XGBoostModelConfig } from '../services/models';
import { APIService } from '../services/api-service';
import { Router, RouterLocation } from '@vaadin/router';
import { InputType, OrInputChangedEvent } from '@openremote/or-mwc-components/or-mwc-input';
import { showSnackbar } from '@openremote/or-mwc-components/or-mwc-snackbar';
import { getRootPath } from '../common/util';
import { DurationInputType, TimeDurationUnit } from '../components/custom-duration-input';
import { consume } from '@lit/context';
import { realmContext } from './app-layout';
import { manager } from '@openremote/core';
import * as Model from '@openremote/model';

@customElement('page-config-editor')
export class PageConfigEditor extends LitElement {
    @consume({ context: realmContext })
    realm = '';

    static get styles() {
        return css`
            :host {
                --or-panel-background-color: #fff;
                --or-panel-heading-text-transform: uppercase;
                --or-panel-heading-color: var(--or-app-color3);
                --or-panel-heading-font-size: 14px;
            }

            hr {
                border: 0;
                height: 1px;
                background-color: var(--or-app-color5);
                margin: 5px 0;
            }

            .config-editor {
                display: flex;
                flex-direction: column;
                gap: 16px;
                padding: 5px 0px;
            }

            .row {
                display: flex;
                flex-direction: row;
                flex: 1 1 0;
                gap: 24px;
            }

            .regressor-row {
                padding: 10px 0px;
            }

            .column {
                display: flex;
                flex-direction: column;
                flex: 1 1 0;
                gap: 20px;
                padding: 0px 0px 10px 0px;
            }

            or-mwc-input {
                flex: 1;
                max-width: 350px;
            }

            or-mwc-input[type='checkbox'] {
                flex: none;
            }

            .config-header {
                width: 100%;
                display: flex;
                flex-direction: row;
                align-items: center;
                justify-content: space-between;
            }

            .config-header-name {
                display: flex;
                width: 100%;
                gap: 20px;
            }
        `;
    }

    @property({ type: String })
    configId?: string;

    @state()
    protected modelConfig: ModelConfig | null = null;

    @state()
    protected assetSelectList: Map<string, string> = new Map();

    @state()
    protected attributeSelectList: Map<string, Map<string, string>> = new Map();

    @state()
    protected loading: boolean = true;

    @state()
    protected isValid: boolean = false;

    @state()
    protected modified: boolean = false;

    @state()
    protected error: string | null = null;

    protected readonly rootPath = getRootPath();

    @state()
    protected formData: ModelConfig = {
        type: ModelTypeEnum.PROPHET,
        realm: '', // Set during setup
        name: 'New Model Config',
        enabled: true,
        target: {
            asset_id: '',
            attribute_name: '',
            training_data_period: 'P6M'
        },
        regressors: null,
        forecast_interval: 'PT1H',
        forecast_periods: 24,
        forecast_frequency: '1h',
        daily_seasonality: true,
        weekly_seasonality: true,
        yearly_seasonality: true,
        changepoint_range: 0.8,
        changepoint_prior_scale: 0.05,
        seasonality_mode: ProphetSeasonalityModeEnum.ADDITIVE
    } as ProphetModelConfig;

    // Handle basic form field updates
    protected handleBasicInput(ev: OrInputChangedEvent | CustomEvent<{ value: string }>) {
        const value = 'detail' in ev ? ev.detail?.value : undefined;
        const target = ev.target as HTMLInputElement;

        if (!target || value === undefined) {
            return;
        }

        // Handle model type change specially
        if (target.name === 'type') {
            this.handleModelTypeChange(value as ModelTypeEnum);
            return;
        }

        this.formData = {
            ...this.formData,
            [target.name]: value
        };
    }

    // Handle model type changes and reset to appropriate defaults
    protected handleModelTypeChange(newType: ModelTypeEnum) {
        const baseConfig = {
            type: newType,
            realm: this.formData.realm,
            name: this.formData.name,
            enabled: this.formData.enabled,
            target: this.formData.target,
            forecast_interval: this.formData.forecast_interval,
            forecast_periods: this.formData.forecast_periods,
            forecast_frequency: this.formData.forecast_frequency,
        };

        if (newType === ModelTypeEnum.PROPHET) {
            this.formData = {
                ...baseConfig,
                type: ModelTypeEnum.PROPHET,
                regressors: null,
                daily_seasonality: true,
                weekly_seasonality: true,
                yearly_seasonality: true,
                changepoint_range: 0.8,
                changepoint_prior_scale: 0.05,
                seasonality_mode: ProphetSeasonalityModeEnum.ADDITIVE
            } as ProphetModelConfig;
        } else if (newType === ModelTypeEnum.XGBOOST) {
            this.formData = {
                ...baseConfig,
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
            } as XGBoostModelConfig;
        }
    }

    // Handle target-specific updates
    protected handleTargetInput(ev: OrInputChangedEvent) {
        const value = ev.detail?.value;
        const target = ev.target as HTMLInputElement;

        if (!target || value === undefined) {
            return;
        }

        const [, field] = target.name.split('.');
        if (!field) {
            console.error('Invalid target input name:', target.name);
            return;
        }

        // Auto-select first attribute when asset changes
        if (field === 'asset_id') {
            this.formData.target.attribute_name =
                this.attributeSelectList
                    .get(value as string)
                    ?.values()
                    .next().value ?? '';
        }

        this.formData = {
            ...this.formData,
            target: {
                ...this.formData.target,
                [field]: value
            }
        };
    }

    // Handle regressor-specific updates
    protected handleRegressorInput(ev: OrInputChangedEvent, index: number) {
        const value = ev.detail?.value;
        const target = ev.target as HTMLInputElement;

        const prophetConfig = this.formData as ProphetModelConfig;
        if (!target || value === undefined || !prophetConfig.regressors) {
            return;
        }

        // Auto-select first attribute when asset changes
        if (target.name === 'asset_id') {
            prophetConfig.regressors[index].attribute_name =
                this.attributeSelectList
                    .get(value as string)
                    ?.values()
                    .next().value ?? '';
        }

        prophetConfig.regressors[index] = {
            ...prophetConfig.regressors[index],
            [target.name]: value
        };
        this.requestUpdate();
    }

    willUpdate(_changedProperties: PropertyValues): void {
        void _changedProperties; // Explicitly acknowledge unused parameter
        this.isValid = this.isFormValid();
        this.modified = this.isFormModified();
    }

    // Set up all the data for the editor
    protected async setupEditor() {
        this.formData.realm = this.realm;

        await this.loadAssets();
        await this.loadConfig();
    }

    // Loads assets and attributes that store data points e.g. have history
    protected async loadAssets() {
        this.assetSelectList.clear();
        try {
            const assetQuery: Model.AssetQuery = {
                realm: {
                    name: this.realm
                },
                attributes: {
                    operator: Model.LogicGroupOperator.AND,
                    items: [
                        {
                            meta: [
                                {
                                    name: {
                                        predicateType: 'string',
                                        match: Model.AssetQueryMatch.EXACT,
                                        caseSensitive: true,
                                        value: 'storeDataPoints'
                                    },
                                    value: {
                                        predicateType: 'boolean',
                                        value: true
                                    }
                                }
                            ]
                        }
                    ]
                }
            };

            const response = await manager.rest.api.AssetResource.queryAssets(assetQuery);
            const assets = response.data;

            // remove attributes that do not have the meta attribute "storeDataPoints" set to true
            assets.forEach((asset) => {
                Object.values(asset.attributes ?? {}).forEach((attribute) => {
                    if (attribute.meta?.storeDataPoints !== true) {
                        delete asset.attributes?.[attribute.name as keyof typeof asset.attributes];
                    }
                });
            });

            assets.forEach((asset) => {
                this.assetSelectList.set(asset.id ?? '', asset.name ?? '');
                this.attributeSelectList.set(
                    asset.id ?? '',
                    new Map(Object.entries(asset.attributes ?? {}).map(([key, value]) => [key, value.name ?? '']))
                );
            });
        } catch (err) {
            console.error(err);
            this.error = `Failed to retrieve assets needed for the forecast configuration`;
        }
    }

    // Try to load the config from the API
    protected async loadConfig() {
        this.loading = true;
        this.isValid = false;

        if (!this.configId) {
            this.loading = false;
            return;
        }
        try {
            this.modelConfig = await APIService.getModelConfig(this.realm, this.configId);
            // Create a deep copy of the model config for the form data
            this.formData = JSON.parse(JSON.stringify(this.modelConfig));
            this.loading = false;
            return;
        } catch (err) {
            this.loading = false;
            console.error(err);
            this.error = `Failed to retrieve the forecast configuration`;
        }
    }

    // Handle the Vaadin Router location change event
    onAfterEnter(location: RouterLocation) {
        this.configId = location.params.id as string;
        return this.setupEditor();
    }

    // Handle the save button click
    async onSave() {
        const isExistingConfig = this.modelConfig !== null;

        // Switch between update and create -- based on whether the config exists
        const saveRequest =
            isExistingConfig && this.configId
                ? APIService.updateModelConfig(this.realm, this.configId, this.formData)
                : APIService.createModelConfig(this.realm, this.formData);

        try {
            const modelConfig = await saveRequest;
            if (isExistingConfig) {
                await this.loadConfig();
            } else {
                Router.go(`${this.rootPath}/${modelConfig.realm}/configs/${modelConfig.id}`);
            }
        } catch (error) {
            console.error(error);
            showSnackbar(undefined, 'Failed to save the config');
        }
    }

    // Check form for validity
    isFormValid() {
        // check target properties
        if (!this.formData.target.asset_id || !this.formData.target.attribute_name) {
            return false;
        }

        // check all covariates/regressors based on model type
        if (this.formData.type === ModelTypeEnum.PROPHET) {
            const prophetConfig = this.formData as ProphetModelConfig;
            if (prophetConfig.regressors) {
                for (const regressor of prophetConfig.regressors) {
                    if (!regressor.asset_id || !regressor.attribute_name) {
                        return false;
                    }
                }
            }
        } else if (this.formData.type === ModelTypeEnum.XGBOOST) {
            const xgboostConfig = this.formData as XGBoostModelConfig;
            if (xgboostConfig.past_covariates) {
                for (const covariate of xgboostConfig.past_covariates) {
                    if (!covariate.asset_id || !covariate.attribute_name) {
                        return false;
                    }
                }
            }
            if (xgboostConfig.future_covariates) {
                for (const covariate of xgboostConfig.future_covariates) {
                    if (!covariate.asset_id || !covariate.attribute_name) {
                        return false;
                    }
                }
            }
        }

        // Check other inputs
        const inputs = this.shadowRoot?.querySelectorAll('or-mwc-input') as NodeListOf<HTMLInputElement>;
        if (inputs) {
            return Array.from(inputs).every((input) => input.checkValidity());
        }
        return false;
    }

    // Check if the form has been modified
    isFormModified() {
        return JSON.stringify(this.formData) !== JSON.stringify(this.modelConfig);
    }

    // Get the parameters template based on model type
    getParametersTemplate() {
        if (this.formData.type === ModelTypeEnum.PROPHET) {
            return this.getProphetParametersTemplate();
        } else if (this.formData.type === ModelTypeEnum.XGBOOST) {
            return this.getXGBoostParametersTemplate();
        }
        return html``;
    }

    // Prophet-specific parameters
    getProphetParametersTemplate() {
        const prophetConfig = this.formData as ProphetModelConfig;
        return html`
            <or-panel heading="PROPHET PARAMETERS">
                <div class="column">
                    <div class="row">
                        <!-- changepoint_range -->
                        <or-mwc-input
                            type="${InputType.NUMBER}"
                            name="changepoint_range"
                            @or-mwc-input-changed="${this.handleBasicInput}"
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
                            @or-mwc-input-changed="${this.handleBasicInput}"
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
                            @or-mwc-input-changed="${this.handleBasicInput}"
                            label="Seasonality mode"
                            .value="${prophetConfig.seasonality_mode}"
                            required
                        ></or-mwc-input>
                        <!-- daily_seasonality -->
                        <or-mwc-input
                            type="${InputType.CHECKBOX}"
                            name="daily_seasonality"
                            @or-mwc-input-changed="${this.handleBasicInput}"
                            label="Daily seasonality"
                            .value="${prophetConfig.daily_seasonality}"
                        ></or-mwc-input>
                        <!-- weekly_seasonality -->
                        <or-mwc-input
                            type="${InputType.CHECKBOX}"
                            name="weekly_seasonality"
                            @or-mwc-input-changed="${this.handleBasicInput}"
                            label="Weekly seasonality"
                            .value="${prophetConfig.weekly_seasonality}"
                        ></or-mwc-input>
                        <!-- yearly_seasonality -->
                        <or-mwc-input
                            type="${InputType.CHECKBOX}"
                            name="yearly_seasonality"
                            @or-mwc-input-changed="${this.handleBasicInput}"
                            label="Yearly seasonality"
                            .value="${prophetConfig.yearly_seasonality}"
                        ></or-mwc-input>
                    </div>
                </div>
            </or-panel>
        `;
    }

    // XGBoost-specific parameters
    getXGBoostParametersTemplate() {
        const xgboostConfig = this.formData as XGBoostModelConfig;
        return html`
            <or-panel heading="XGBOOST PARAMETERS">
                <div class="column">
                    <div class="row">
                        <!-- lags -->
                        <or-mwc-input
                            type="${InputType.NUMBER}"
                            name="lags"
                            @or-mwc-input-changed="${this.handleBasicInput}"
                            label="Lags"
                            .value="${xgboostConfig.lags}"
                            min="1"
                            required
                        ></or-mwc-input>
                        <!-- output_chunk_length -->
                        <or-mwc-input
                            type="${InputType.NUMBER}"
                            name="output_chunk_length"
                            @or-mwc-input-changed="${this.handleBasicInput}"
                            label="Output chunk length"
                            .value="${xgboostConfig.output_chunk_length}"
                            min="1"
                            required
                        ></or-mwc-input>
                        <!-- n_estimators -->
                        <or-mwc-input
                            type="${InputType.NUMBER}"
                            name="n_estimators"
                            @or-mwc-input-changed="${this.handleBasicInput}"
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
                            @or-mwc-input-changed="${this.handleBasicInput}"
                            label="Max depth"
                            .value="${xgboostConfig.max_depth}"
                            min="1"
                            required
                        ></or-mwc-input>
                        <!-- learning_rate -->
                        <or-mwc-input
                            type="${InputType.NUMBER}"
                            name="learning_rate"
                            @or-mwc-input-changed="${this.handleBasicInput}"
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
                            @or-mwc-input-changed="${this.handleBasicInput}"
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
                            @or-mwc-input-changed="${this.handleBasicInput}"
                            label="Random state"
                            .value="${xgboostConfig.random_state}"
                            min="0"
                        ></or-mwc-input>
                    </div>
                </div>
            </or-panel>
        `;
    }

    // Get covariates template based on model type
    getCovariatesTemplate() {
        if (this.formData.type === ModelTypeEnum.PROPHET) {
            return this.getProphetCovariatesTemplate();
        } else if (this.formData.type === ModelTypeEnum.XGBOOST) {
            return this.getXGBoostCovariatesTemplate();
        }
        return html``;
    }

    // Prophet regressors template
    getProphetCovariatesTemplate() {
        const prophetConfig = this.formData as ProphetModelConfig;
        return html`
            ${when(
                prophetConfig.regressors,
                () => map(prophetConfig.regressors ?? [], (_regressor, index) => this.getRegressorTemplate(index)),
                () => html``
            )}
            ${this.getAddRegressorTemplate()}
        `;
    }

    // XGBoost covariates template
    getXGBoostCovariatesTemplate() {
        const xgboostConfig = this.formData as XGBoostModelConfig;
        return html`
            ${when(
                xgboostConfig.past_covariates,
                () => map(xgboostConfig.past_covariates ?? [], (_covariate, index) => this.getPastCovariateTemplate(index)),
                () => html``
            )}
            ${this.getAddPastCovariateTemplate()}
            
            ${when(
                xgboostConfig.future_covariates,
                () => map(xgboostConfig.future_covariates ?? [], (_covariate, index) => this.getFutureCovariateTemplate(index)),
                () => html``
            )}
            ${this.getAddFutureCovariateTemplate()}
        `;
    }

    // Handle adding a regressor
    handleAddRegressor() {
        const prophetConfig = this.formData as ProphetModelConfig;
        prophetConfig.regressors = prophetConfig.regressors ?? [];

        prophetConfig.regressors.push({
            asset_id: '',
            attribute_name: '',
            training_data_period: 'P6M'
        });
        this.requestUpdate();
    }

    // Handle deleting a regressor
    handleDeleteRegressor(index: number) {
        const prophetConfig = this.formData as ProphetModelConfig;
        if (!prophetConfig.regressors) {
            return;
        }

        prophetConfig.regressors.splice(index, 1);

        // Clean up regressors if all are deleted
        if (prophetConfig.regressors?.length === 0) {
            prophetConfig.regressors = null;
        }

        this.requestUpdate();
    }

    // Get the regressor template
    getRegressorTemplate(index: number) {
        const prophetConfig = this.formData as ProphetModelConfig;
        if (!prophetConfig.regressors) {
            return;
        }

        const regressor = prophetConfig.regressors[index];
        return html`
            <or-panel heading="REGRESSOR ${index + 1}">
                <div class="column">
                    <div class="row">
                        <or-mwc-input
                            type="${InputType.SELECT}"
                            name="asset_id"
                            @or-mwc-input-changed="${(e: OrInputChangedEvent) => this.handleRegressorInput(e, index)}"
                            label="Asset"
                            .value="${regressor.asset_id}"
                            .options="${[...this.assetSelectList.entries()]}"
                            .searchProvider="${this.assetSelectList.size > 0 ? this.searchAssets.bind(this) : null}"
                        ></or-mwc-input>

                        <!-- Render the attribute select list if the asset is selected -->
                        ${when(
                            regressor.asset_id,
                            () => html`
                                <or-mwc-input
                                    type="${InputType.SELECT}"
                                    name="attribute_name"
                                    @or-mwc-input-changed="${(e: OrInputChangedEvent) => this.handleRegressorInput(e, index)}"
                                    label="Attribute"
                                    .value="${regressor.attribute_name}"
                                    .options="${[...(this.attributeSelectList.get(regressor.asset_id) ?? new Map())]}"
                                ></or-mwc-input>
                            `,
                            () => html`
                                <or-mwc-input type="${InputType.SELECT}" name="attribute_name" label="Attribute" disabled></or-mwc-input>
                            `
                        )}

                        <custom-duration-input
                            name="training_data_period"
                            .type="${DurationInputType.ISO_8601}"
                            @value-changed="${(e: OrInputChangedEvent) => this.handleRegressorInput(e, index)}"
                            label="Training data period"
                            .iso_units="${[TimeDurationUnit.DAY, TimeDurationUnit.WEEK, TimeDurationUnit.MONTH, TimeDurationUnit.YEAR]}"
                            .value="${regressor.training_data_period}"
                        ></custom-duration-input>

                        <or-mwc-input
                            style="max-width: 48px;"
                            type="${InputType.BUTTON}"
                            icon="delete"
                            @click="${() => this.handleDeleteRegressor(index)}"
                        ></or-mwc-input>
                    </div>
                </div>
            </or-panel>
        `;
    }

    // Get the add regressor template
    getAddRegressorTemplate() {
        return html`
            <or-panel>
                <div class="row regressor-row">
                    <or-mwc-input
                        type="${InputType.BUTTON}"
                        icon="plus"
                        label="add regressor"
                        @click="${this.handleAddRegressor}"
                    ></or-mwc-input>
                </div>
            </or-panel>
        `;
    }

    // XGBoost Past Covariate methods
    handleAddPastCovariate() {
        const xgboostConfig = this.formData as XGBoostModelConfig;
        xgboostConfig.past_covariates = xgboostConfig.past_covariates ?? [];
        
        xgboostConfig.past_covariates.push({
            asset_id: '',
            attribute_name: '',
            training_data_period: 'P6M'
        });
        this.requestUpdate();
    }

    handleDeletePastCovariate(index: number) {
        const xgboostConfig = this.formData as XGBoostModelConfig;
        if (!xgboostConfig.past_covariates) return;
        
        xgboostConfig.past_covariates.splice(index, 1);
        if (xgboostConfig.past_covariates.length === 0) {
            xgboostConfig.past_covariates = null;
        }
        this.requestUpdate();
    }

    getPastCovariateTemplate(index: number) {
        const xgboostConfig = this.formData as XGBoostModelConfig;
        if (!xgboostConfig.past_covariates) return;
        
        const covariate = xgboostConfig.past_covariates[index];
        return html`
            <or-panel heading="PAST COVARIATE ${index + 1}">
                <div class="column">
                    <div class="row">
                        <or-mwc-input
                            type="${InputType.SELECT}"
                            name="asset_id"
                            @or-mwc-input-changed="${(e: OrInputChangedEvent) => this.handlePastCovariateInput(e, index)}"
                            label="Asset"
                            .value="${covariate.asset_id}"
                            .options="${[...this.assetSelectList.entries()]}"
                            .searchProvider="${this.assetSelectList.size > 0 ? this.searchAssets.bind(this) : null}"
                        ></or-mwc-input>

                        ${when(
                            covariate.asset_id,
                            () => html`
                                <or-mwc-input
                                    type="${InputType.SELECT}"
                                    name="attribute_name"
                                    @or-mwc-input-changed="${(e: OrInputChangedEvent) => this.handlePastCovariateInput(e, index)}"
                                    label="Attribute"
                                    .value="${covariate.attribute_name}"
                                    .options="${[...(this.attributeSelectList.get(covariate.asset_id) ?? new Map())]}"
                                ></or-mwc-input>
                            `,
                            () => html`
                                <or-mwc-input type="${InputType.SELECT}" name="attribute_name" label="Attribute" disabled></or-mwc-input>
                            `
                        )}

                        <custom-duration-input
                            name="training_data_period"
                            .type="${DurationInputType.ISO_8601}"
                            @value-changed="${(e: OrInputChangedEvent) => this.handlePastCovariateInput(e, index)}"
                            label="Training data period"
                            .iso_units="${[TimeDurationUnit.DAY, TimeDurationUnit.WEEK, TimeDurationUnit.MONTH, TimeDurationUnit.YEAR]}"
                            .value="${covariate.training_data_period}"
                        ></custom-duration-input>

                        <or-mwc-input
                            style="max-width: 48px;"
                            type="${InputType.BUTTON}"
                            icon="delete"
                            @click="${() => this.handleDeletePastCovariate(index)}"
                        ></or-mwc-input>
                    </div>
                </div>
            </or-panel>
        `;
    }

    getAddPastCovariateTemplate() {
        return html`
            <or-panel>
                <div class="row regressor-row">
                    <or-mwc-input
                        type="${InputType.BUTTON}"
                        icon="plus"
                        label="add past covariate"
                        @click="${this.handleAddPastCovariate}"
                    ></or-mwc-input>
                </div>
            </or-panel>
        `;
    }

    handlePastCovariateInput(ev: OrInputChangedEvent, index: number) {
        const value = ev.detail?.value;
        const target = ev.target as HTMLInputElement;
        const xgboostConfig = this.formData as XGBoostModelConfig;

        if (!target || value === undefined || !xgboostConfig.past_covariates) return;

        if (target.name === 'asset_id') {
            xgboostConfig.past_covariates[index].attribute_name =
                this.attributeSelectList.get(value as string)?.values().next().value ?? '';
        }

        xgboostConfig.past_covariates[index] = {
            ...xgboostConfig.past_covariates[index],
            [target.name]: value
        };
        this.requestUpdate();
    }

    // XGBoost Future Covariate methods (similar structure)
    handleAddFutureCovariate() {
        const xgboostConfig = this.formData as XGBoostModelConfig;
        xgboostConfig.future_covariates = xgboostConfig.future_covariates ?? [];
        
        xgboostConfig.future_covariates.push({
            asset_id: '',
            attribute_name: '',
            training_data_period: 'P6M'
        });
        this.requestUpdate();
    }

    handleDeleteFutureCovariate(index: number) {
        const xgboostConfig = this.formData as XGBoostModelConfig;
        if (!xgboostConfig.future_covariates) return;
        
        xgboostConfig.future_covariates.splice(index, 1);
        if (xgboostConfig.future_covariates.length === 0) {
            xgboostConfig.future_covariates = null;
        }
        this.requestUpdate();
    }

    getFutureCovariateTemplate(index: number) {
        const xgboostConfig = this.formData as XGBoostModelConfig;
        if (!xgboostConfig.future_covariates) return;
        
        const covariate = xgboostConfig.future_covariates[index];
        return html`
            <or-panel heading="FUTURE COVARIATE ${index + 1}">
                <div class="column">
                    <div class="row">
                        <or-mwc-input
                            type="${InputType.SELECT}"
                            name="asset_id"
                            @or-mwc-input-changed="${(e: OrInputChangedEvent) => this.handleFutureCovariateInput(e, index)}"
                            label="Asset"
                            .value="${covariate.asset_id}"
                            .options="${[...this.assetSelectList.entries()]}"
                            .searchProvider="${this.assetSelectList.size > 0 ? this.searchAssets.bind(this) : null}"
                        ></or-mwc-input>

                        ${when(
                            covariate.asset_id,
                            () => html`
                                <or-mwc-input
                                    type="${InputType.SELECT}"
                                    name="attribute_name"
                                    @or-mwc-input-changed="${(e: OrInputChangedEvent) => this.handleFutureCovariateInput(e, index)}"
                                    label="Attribute"
                                    .value="${covariate.attribute_name}"
                                    .options="${[...(this.attributeSelectList.get(covariate.asset_id) ?? new Map())]}"
                                ></or-mwc-input>
                            `,
                            () => html`
                                <or-mwc-input type="${InputType.SELECT}" name="attribute_name" label="Attribute" disabled></or-mwc-input>
                            `
                        )}

                        <custom-duration-input
                            name="training_data_period"
                            .type="${DurationInputType.ISO_8601}"
                            @value-changed="${(e: OrInputChangedEvent) => this.handleFutureCovariateInput(e, index)}"
                            label="Training data period"
                            .iso_units="${[TimeDurationUnit.DAY, TimeDurationUnit.WEEK, TimeDurationUnit.MONTH, TimeDurationUnit.YEAR]}"
                            .value="${covariate.training_data_period}"
                        ></custom-duration-input>

                        <or-mwc-input
                            style="max-width: 48px;"
                            type="${InputType.BUTTON}"
                            icon="delete"
                            @click="${() => this.handleDeleteFutureCovariate(index)}"
                        ></or-mwc-input>
                    </div>
                </div>
            </or-panel>
        `;
    }

    getAddFutureCovariateTemplate() {
        return html`
            <or-panel>
                <div class="row regressor-row">
                    <or-mwc-input
                        type="${InputType.BUTTON}"
                        icon="plus"
                        label="add future covariate"
                        @click="${this.handleAddFutureCovariate}"
                    ></or-mwc-input>
                </div>
            </or-panel>
        `;
    }

    handleFutureCovariateInput(ev: OrInputChangedEvent, index: number) {
        const value = ev.detail?.value;
        const target = ev.target as HTMLInputElement;
        const xgboostConfig = this.formData as XGBoostModelConfig;

        if (!target || value === undefined || !xgboostConfig.future_covariates) return;

        if (target.name === 'asset_id') {
            xgboostConfig.future_covariates[index].attribute_name =
                this.attributeSelectList.get(value as string)?.values().next().value ?? '';
        }

        xgboostConfig.future_covariates[index] = {
            ...xgboostConfig.future_covariates[index],
            [target.name]: value
        };
        this.requestUpdate();
    }

    // Search provider for the asset select list
    protected async searchAssets(search?: string): Promise<[any, string][]> {
        const options = [...this.assetSelectList.entries()];
        if (!search) {
            return options;
        }
        const searchTerm = search.toLowerCase();
        return options.filter(([, label]) => label.toLowerCase().includes(searchTerm));
    }

    // Render the editor
    protected render() {
        if (this.loading) {
            return html`<loading-spinner></loading-spinner>`;
        }

        // Display any errors that prevent the editor from being used
        if (this.error) {
            return html`
                <or-panel>
                    <div class="column">
                        <div class="row">
                            <alert-message .alert="${this.error}"></alert-message>
                        </div>
                    </div>
                </or-panel>
            `;
        }

        return html`
            <form id="config-form" class="config-editor">
                <div class="config-header">
                    <div class="config-header-name">
                        <or-mwc-input
                            name="name"
                            focused
                            outlined
                            type="${InputType.TEXT}"
                            label="Model Name"
                            @or-mwc-input-changed="${this.handleBasicInput}"
                            .value="${this.formData.name}"
                            required
                            minlength="1"
                            maxlength="255"
                        ></or-mwc-input>

                        <or-mwc-input
                            type="${InputType.CHECKBOX}"
                            name="enabled"
                            @or-mwc-input-changed="${this.handleBasicInput}"
                            label="Enabled"
                            .value="${this.formData.enabled}"
                        ></or-mwc-input>
                    </div>

                    <!-- Note: I know this is odd, but the disable state would not update properly via the disabled/.disabled/?disabled attribute -->
                    <div class="config-header-controls">
                        ${when(
                            this.isValid && this.modified,
                            () => html`
                                <or-mwc-input
                                    type="${InputType.BUTTON}"
                                    id="save-btn"
                                    label="save"
                                    raised
                                    @click="${this.onSave}"
                                ></or-mwc-input>
                            `,
                            () => html`
                                <or-mwc-input type="${InputType.BUTTON}" id="save-btn" label="save" raised disabled></or-mwc-input>
                            `
                        )}
                    </div>
                </div>

                <!-- Model selection -->
                <or-panel heading="MODEL">
                    <div class="column">
                        <div class="row">
                            <or-mwc-input
                                class="header-item"
                                name="type"
                                required
                                @or-mwc-input-changed="${this.handleBasicInput}"
                                label="Model Type"
                                type="${InputType.SELECT}"
                                .options="${[['prophet', 'Prophet'], ['xgboost', 'XGBoost']]}"
                                .value="${this.formData.type}"
                            >
                            </or-mwc-input>
                        </div>
                    </div>
                </or-panel>

                <!-- Forecast generation, e.g. the schedule -->
                <or-panel heading="FORECAST GENERATION">
                    <div class="column">
                        <div class="row">
                            <!-- forecast_interval (ISO 8601) -->
                            <custom-duration-input
                                name="forecast_interval"
                                .type="${DurationInputType.ISO_8601}"
                                @value-changed="${this.handleBasicInput}"
                                label="Generate new forecast every"
                                .value="${this.formData.forecast_interval}"
                            ></custom-duration-input>
                        </div>

                        <div class="row">
                            <!-- forecast_periods -->
                            <or-mwc-input
                                type="${InputType.NUMBER}"
                                name="forecast_periods"
                                @or-mwc-input-changed="${this.handleBasicInput}"
                                label="Forecasted datapoints"
                                .value="${this.formData.forecast_periods}"
                                required
                            ></or-mwc-input>

                            <!-- forecast_frequency (pandas frequency) -->
                            <custom-duration-input
                                name="forecast_frequency"
                                .type="${DurationInputType.PANDAS_FREQ}"
                                @value-changed="${this.handleBasicInput}"
                                label="Time between datapoints"
                                .value="${this.formData.forecast_frequency}"
                            ></custom-duration-input>
                        </div>
                    </div>
                </or-panel>

                <!-- Forecast target, the asset and attribute to forecast -->
                <or-panel heading="FORECAST TARGET">
                    <div class="column">
                        <div class="row">
                            <or-mwc-input
                                type="${InputType.SELECT}"
                                name="target.asset_id"
                                @or-mwc-input-changed="${this.handleTargetInput}"
                                label="Asset"
                                .value="${this.formData.target.asset_id}"
                                .options="${[...this.assetSelectList.entries()]}"
                                .searchProvider="${this.assetSelectList.size > 0 ? this.searchAssets.bind(this) : null}"
                            ></or-mwc-input>

                            <!-- Render the attribute select list if the asset is selected -->
                            ${when(
                                this.formData.target.asset_id,
                                () => html`
                                    <or-mwc-input
                                        type="${InputType.SELECT}"
                                        name="target.attribute_name"
                                        @or-mwc-input-changed="${this.handleTargetInput}"
                                        label="Attribute"
                                        .value="${this.formData.target.attribute_name}"
                                        .options="${[...(this.attributeSelectList.get(this.formData.target.asset_id) ?? new Map())]}"
                                    ></or-mwc-input>
                                `,
                                () => html`
                                    <or-mwc-input
                                        type="${InputType.SELECT}"
                                        name="target.attribute_name"
                                        label="Attribute"
                                        disabled
                                    ></or-mwc-input>
                                `
                            )}

                            <!-- target.training_data_period -->
                            <custom-duration-input
                                name="target.training_data_period"
                                .type="${DurationInputType.ISO_8601}"
                                @value-changed="${this.handleTargetInput}"
                                label="Training data period"
                                .iso_units="${[TimeDurationUnit.DAY, TimeDurationUnit.WEEK, TimeDurationUnit.MONTH, TimeDurationUnit.YEAR]}"
                                .value="${this.formData.target.training_data_period}"
                            ></custom-duration-input>
                        </div>
                    </div>
                </or-panel>


                <!-- Model parameters, these will be dynamic based on the model type -->
                ${this.getParametersTemplate()}
                <hr />
                <!-- Covariates/Regressors -->
                ${this.getCovariatesTemplate()}
            </form>
        `;
    }
}
