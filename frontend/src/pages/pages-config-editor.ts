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

import { css, html, PropertyValues } from 'lit';
import { OrElement } from '@openremote/or-element';
import '@openremote/or-vaadin-components/or-vaadin-combo-box';
import '@openremote/or-vaadin-components/or-vaadin-text-field';
import '@openremote/or-vaadin-components/or-vaadin-number-field';
import '@openremote/or-vaadin-components/or-vaadin-select';
import '@openremote/or-vaadin-components/or-vaadin-checkbox';
import '@openremote/or-vaadin-components/or-vaadin-button';
import type { OrVaadinComboBox } from '@openremote/or-vaadin-components/or-vaadin-combo-box';
import { customElement, property, state } from 'lit/decorators.js';
import { when } from 'lit/directives/when.js';
import { guard } from 'lit/directives/guard.js';
import { ModelTypeEnum } from '../services/models';
import type { ModelConfig } from '../services/models';
import { APIService } from '../services/api-service';
import { Router, RouterLocation } from '@vaadin/router';
import { showSnackbar } from '@openremote/or-mwc-components/or-mwc-snackbar';
import { getRootPath } from '../common/util';
import { CustomDurationInput, DurationInputType, TimeDurationUnit } from '../components/custom-duration-input';
import { consume } from '@lit/context';
import { realmContext } from './app-layout';
import { manager } from '@openremote/core';
import * as Model from '@openremote/model';
import { ModelTypeRegistry } from './model-configs/model-registry';
import { XGBoostConfig } from './model-configs/xgboost-config';
import type { CovariateLagsInput } from '../components/covariate-lags-input';

// Initialize model configurations
ModelTypeRegistry.registerAllConfigs();

@customElement('page-config-editor')
export class PageConfigEditor extends OrElement {
    @consume({ context: realmContext })
    realm = '';

    static get styles() {
        return css`
            :host {
                display: block;
                min-width: 0;
                --or-panel-background-color: #fff;
                --or-panel-heading-text-transform: none;
                --or-panel-heading-color: var(--or-app-color3);
                --or-panel-heading-font-size: 14px;
                --vaadin-input-field-label-font-weight: 400;
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
                align-items: flex-end;
                flex: 1 1 0;
                gap: 16px;
                flex-wrap: wrap;
            }

            [hidden] {
                display: none !important;
            }

            .regressor-row {
                padding: 10px 0px;
            }

            .column {
                display: flex;
                flex-direction: column;
                flex: 1 1 0;
                gap: 16px;
            }

            or-vaadin-combo-box,
            or-vaadin-text-field,
            or-vaadin-number-field,
            or-vaadin-select {
                flex: 1 1 220px;
                min-width: 0;
                max-width: 350px;
            }

            custom-duration-input {
                flex: 1 1 300px;
                max-width: 350px;
                min-width: 0;
            }

            or-vaadin-checkbox,
            or-vaadin-button {
                flex: none;
            }

            .config-header-controls {
                display: flex;
                justify-content: flex-end;
            }

            .regressor-add {
                align-self: flex-start;
            }

            .config-header-name {
                display: flex;
                flex-direction: column;
                gap: 8px;
                align-items: flex-start;
            }

            .config-header-name or-vaadin-text-field {
                flex: none;
                width: 100%;
            }

            .input-help {
                margin: 0;
                line-height: 1.5;
                color: var(--lumo-secondary-text-color);
                max-width: 80ch;
            }

            .config-group {
                min-width: 0;
                border-radius: var(--lumo-border-radius-l);
                background: color-mix(in srgb, var(--lumo-base-color) 95%, var(--lumo-contrast));
            }

            .config-group > summary {
                cursor: pointer;
                padding: 16px;
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 16px;
                list-style: none;
                font-size: var(--lumo-font-size-l);
                font-weight: 600;
                line-height: 1.25;
                color: var(--lumo-header-text-color);
            }

            .config-group > summary::-webkit-details-marker {
                display: none;
            }

            .config-group > summary::after {
                content: '';
                width: 6px;
                height: 6px;
                flex: none;
                border-right: 2px solid var(--lumo-tertiary-text-color);
                border-bottom: 2px solid var(--lumo-tertiary-text-color);
                transform: rotate(-45deg);
            }

            .config-group[open] > summary::after {
                transform: rotate(45deg);
            }

            .config-group > summary:focus-visible {
                outline: 2px solid var(--lumo-primary-color);
                outline-offset: -2px;
                border-radius: var(--lumo-border-radius-l);
            }

            .group-content {
                margin: 0 16px 16px;
                padding: 16px;
                border-radius: var(--lumo-border-radius-l);
                background: var(--lumo-base-color);
            }

            .group-content.column {
                padding: 0;
                background: transparent;
            }

            .group-content.column > .row,
            .group-content.column > section {
                padding: 16px;
                border-radius: var(--lumo-border-radius-l);
                background: var(--lumo-base-color);
            }

            .group-content.column > section:not([aria-label='Forecast target']) > .row {
                flex-direction: column;
                align-items: stretch;
                gap: 8px;
            }

            .group-content.column > section:not([aria-label='Forecast target']) > .row > * {
                flex: none;
            }

            .group-content h3 {
                margin: 0 0 8px;
                font-size: var(--lumo-font-size-m);
                font-weight: 600;
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

    @state()
    protected saveError: string | null = null;

    protected readonly rootPath = getRootPath();

    @state()
    protected formData: ModelConfig = {
        ...XGBoostConfig.defaultConfig,
        type: ModelTypeEnum.XGBOOST,
        realm: '', // Set during setup
        name: 'New Model Config',
        enabled: true,
        target: {
            asset_id: '',
            attribute_name: '',
            training_data_period: 'P6M'
        },
        forecast_interval: 'PT1H',
        forecast_periods: 24,
        forecast_frequency: '1h',
        calendar_timezone: null
    };

    // Handle basic form field updates
    protected handleBasicInput(ev: Event) {
        const target = ev.currentTarget as HTMLInputElement;
        if (!target) return;
        let value: string | number | boolean | number[] | null | undefined;

        if (ev.type === 'input' || ev.type === 'change') {
            value = target.localName === 'or-vaadin-checkbox' ? target.checked : target.value;
            if (target.localName === 'or-vaadin-number-field') {
                value = target.value === '' ? NaN : Number(target.value);
            }
        } else {
            const detail = (ev as CustomEvent<{ value: string | number | number[] | null; valid?: boolean }>).detail;
            if (detail?.valid === false) {
                this.requestUpdate();
                return;
            }
            value = detail?.value;
        }

        if (value === undefined) {
            return;
        }

        this.saveError = null;

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
            forecast_frequency: this.formData.forecast_frequency,
            calendar_timezone: this.formData.calendar_timezone
        };

        this.formData = {
            ...baseConfig,
            ...modelTypeConfig.defaultConfig
        } as ModelConfig;
    }

    // Handle target-specific updates
    protected handleTargetInput(ev: Event) {
        const target = ev.currentTarget as HTMLInputElement | OrVaadinComboBox;
        const value = ev.type === 'change' ? target?.value : (ev as CustomEvent<{ value: string }>).detail?.value;

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
                    ?.keys()
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

    protected async updated() {
        const inputs = this.shadowRoot?.querySelectorAll<CustomDurationInput | CovariateLagsInput>(
            'custom-duration-input, covariate-lags-input'
        );
        await Promise.all(Array.from(inputs ?? [], (input) => input.updateComplete));
        this.isValid = this.isFormValid();
    }

    // Set up all the data for the editor
    protected async setupEditor() {
        this.formData.realm = this.realm;

        await this.loadAssets();
        await this.loadConfig();
    }

    // Loads assets and attributes that store data points e.g. have history
    protected async loadAssets() {
        this.assetSelectList = new Map();
        this.attributeSelectList = new Map();
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
        this.saveError = null;
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
            this.saveError = error instanceof Error ? error.message : 'Could not save the forecast configuration. Try again.';
            showSnackbar(undefined, this.saveError);
        }
    }

    // Check form for validity
    isFormValid() {
        const durations = this.shadowRoot?.querySelectorAll<CustomDurationInput>('custom-duration-input');
        if (durations && !Array.from(durations).every((input) => input.checkValidity())) return false;
        const lagInputs = this.shadowRoot?.querySelectorAll<CovariateLagsInput>('covariate-lags-input');
        if (lagInputs && !Array.from(lagInputs).every((input) => input.checkValidity())) return false;
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
        const inputs = this.shadowRoot?.querySelectorAll<HTMLInputElement | OrVaadinComboBox>(
            'or-vaadin-combo-box, or-vaadin-text-field, or-vaadin-number-field, or-vaadin-select'
        );
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
                <div class="config-header-controls">
                    <or-vaadin-button id="save-btn" theme="primary" ?disabled=${!this.isValid || !this.modified} @click=${this.onSave}>
                        Save
                    </or-vaadin-button>
                </div>

                ${when(this.saveError, () => html`<alert-message .alert=${this.saveError}></alert-message>`)}

                <details class="config-group" open>
                    <summary>Properties</summary>
                    <div class="group-content config-header-name">
                        <or-vaadin-text-field
                            name="name"
                            label="Configuration name"
                            @input=${this.handleBasicInput}
                            .value=${this.formData.name}
                            required
                            minlength="1"
                            maxlength="255"
                        ></or-vaadin-text-field>
                        <or-vaadin-checkbox
                            name="enabled"
                            @change=${this.handleBasicInput}
                            label="Enabled"
                            .checked=${this.formData.enabled}
                        ></or-vaadin-checkbox>
                    </div>
                </details>

                <details class="config-group" open>
                    <summary>Model configuration</summary>
                    <div class="group-content column">
                        <div class="row">
                            <or-vaadin-select
                                name="type"
                                required
                                @change=${this.handleBasicInput}
                                label="Model type"
                                .items=${guard([], () => ModelTypeRegistry.getSelectOptions().map(([value, label]) => ({ value, label })))}
                                .value=${this.formData.type}
                            ></or-vaadin-select>
                        </div>

                        <section aria-label="Forecast generation">
                            <h3>Forecast generation</h3>
                            <div class="row">
                                <custom-duration-input
                                    name="forecast_interval"
                                    .type=${DurationInputType.ISO_8601}
                                    @value-changed=${this.handleBasicInput}
                                    label="Generate new forecast every"
                                    .iso_units=${[
                                        TimeDurationUnit.MINUTE,
                                        TimeDurationUnit.HOUR,
                                        TimeDurationUnit.DAY,
                                        TimeDurationUnit.WEEK
                                    ]}
                                    .value=${this.formData.forecast_interval}
                                ></custom-duration-input>
                                <or-vaadin-number-field
                                    name="forecast_periods"
                                    @input=${this.handleBasicInput}
                                    label="Forecasted datapoints"
                                    .value=${Number.isFinite(this.formData.forecast_periods) ? String(this.formData.forecast_periods) : ''}
                                    min="1"
                                    step="1"
                                    required
                                ></or-vaadin-number-field>
                            </div>
                        </section>

                        <section aria-label="Forecast target">
                            <h3>Forecast target</h3>
                            <div class="row">
                                <or-vaadin-combo-box
                                    name="target.asset_id"
                                    @change=${this.handleTargetInput}
                                    label="Asset"
                                    item-label-path="label"
                                    item-value-path="value"
                                    .items=${guard([this.assetSelectList], () =>
                                        [...this.assetSelectList].map(([value, label]) => ({ value, label }))
                                    )}
                                    .value=${this.formData.target.asset_id}
                                    clear-button-visible
                                    required
                                ></or-vaadin-combo-box>
                                <or-vaadin-combo-box
                                    name="target.attribute_name"
                                    @change=${this.handleTargetInput}
                                    label="Attribute"
                                    item-label-path="label"
                                    item-value-path="value"
                                    .items=${guard([this.attributeSelectList, this.formData.target.asset_id], () =>
                                        [...(this.attributeSelectList.get(this.formData.target.asset_id) ?? new Map())].map(
                                            ([value, label]) => ({ value, label })
                                        )
                                    )}
                                    .value=${this.formData.target.attribute_name}
                                    ?disabled=${!this.formData.target.asset_id}
                                    clear-button-visible
                                    required
                                ></or-vaadin-combo-box>
                            </div>
                        </section>

                        <section aria-label="Data and sampling">
                            <h3>Data and sampling</h3>
                            <div class="row">
                                <custom-duration-input
                                    name="forecast_frequency"
                                    .type=${DurationInputType.PANDAS_FREQ}
                                    @value-changed=${this.handleBasicInput}
                                    label="Time between datapoints"
                                    .value=${this.formData.forecast_frequency}
                                ></custom-duration-input>
                                <custom-duration-input
                                    name="target.training_data_period"
                                    .type=${DurationInputType.ISO_8601}
                                    @value-changed=${this.handleTargetInput}
                                    label="Training data period"
                                    .iso_units=${[
                                        TimeDurationUnit.DAY,
                                        TimeDurationUnit.WEEK,
                                        TimeDurationUnit.MONTH,
                                        TimeDurationUnit.YEAR
                                    ]}
                                    .value=${this.formData.target.training_data_period}
                                ></custom-duration-input>
                            </div>
                        </section>
                    </div>
                </details>

                ${this.getParametersTemplate()} ${this.getCovariatesTemplate()}
            </form>
        `;
    }
}
