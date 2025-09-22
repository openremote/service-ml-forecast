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
import { when } from 'lit/directives/when.js';
import { ModelTypeEnum, ProphetSeasonalityModeEnum } from '../services/models';
import type { ModelConfig, ProphetModelConfig } from '../services/models';
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
import { ModelTypeRegistry } from './model-configs/model-registry';

// Initialize model configurations
ModelTypeRegistry.registerAllConfigs();

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
        const modelTypeConfig = ModelTypeRegistry.get(newType);
        if (!modelTypeConfig) {
            console.error(`Unknown model type: ${newType}`);
            return;
        }

        const baseConfig = {
            id: this.formData.id, // Preserve the existing ID
            realm: this.formData.realm,
            name: this.formData.name,
            enabled: this.formData.enabled,
            target: this.formData.target,
            forecast_interval: this.formData.forecast_interval,
            forecast_periods: this.formData.forecast_periods,
            forecast_frequency: this.formData.forecast_frequency
        };

        this.formData = {
            ...baseConfig,
            ...modelTypeConfig.defaultConfig
        } as ModelConfig;
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

        // Use registry for model-specific validation
        const modelTypeConfig = ModelTypeRegistry.get(this.formData.type);
        if (modelTypeConfig && !modelTypeConfig.validateConfig(this.formData)) {
            return false;
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
        const modelTypeConfig = ModelTypeRegistry.get(this.formData.type);
        if (!modelTypeConfig) {
            return html`<div>Unknown model type: ${this.formData.type}</div>`;
        }
        return modelTypeConfig.getParametersTemplate(this.formData, this.handleBasicInput.bind(this));
    }

    // Get covariates template based on model type
    getCovariatesTemplate() {
        const modelTypeConfig = ModelTypeRegistry.get(this.formData.type);
        if (!modelTypeConfig) {
            return html`<div>Unknown model type: ${this.formData.type}</div>`;
        }

        return modelTypeConfig.getCovariatesTemplate(this.formData, {
            assetSelectList: this.assetSelectList,
            attributeSelectList: this.attributeSelectList,
            searchAssets: this.searchAssets.bind(this),
            requestUpdate: this.requestUpdate.bind(this),
            handleInput: () => {} // Not used in current implementation
        });
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
                                .options="${ModelTypeRegistry.getSelectOptions()}"
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
