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

import { css, html, LitElement } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { map } from 'lit/directives/map.js';
import { when } from 'lit/directives/when.js';
import { ModelTypeEnum, ProphetSeasonalityModeEnum } from '../services/models';
import type { ITransformerModelConfig, ModelConfig, NLEnergyForecasterModelConfig, ProphetModelConfig } from '../services/models';
import { APIService } from '../services/api-service';
import { Router, RouterLocation } from '@vaadin/router';
import { InputType, OrInputChangedEvent } from '@openremote/or-mwc-components/or-mwc-input';
import { showSnackbar } from '@openremote/or-mwc-components/or-mwc-snackbar';
import { showDialog } from '@openremote/or-mwc-components/or-mwc-dialog';
import { getRootPath } from '../common/util';
import { DurationInputType, TimeDurationUnit } from '../components/custom-duration-input';
import { consume } from '@lit/context';
import { realmContext } from './app-layout';
import { manager, Util } from '@openremote/core';
import { CustomAssetAttributePicker } from '../components/custom-asset-attribute-picker';
import { OrAssetAttributePickerPickedEvent } from '@openremote/or-attribute-picker';
import { getAssetDescriptorIconTemplate } from '@openremote/or-icon';
import { Asset, AssetModelUtil } from '@openremote/model';

const BASE_FORM_DEFAULTS = {
    realm: '',
    name: 'New Model Config',
    enabled: true as const,
    target: { asset_id: '', attribute_name: '', training_data_period: 'P6M' },
    regressors: null as null,
    forecast_interval: 'PT1H',
    forecast_periods: 24,
    forecast_frequency: '1h'
};

const DEFAULT_PROPHET_FORM_DATA = (realm: string): ProphetModelConfig => ({
    ...BASE_FORM_DEFAULTS,
    realm,
    type: ModelTypeEnum.PROPHET,
    daily_seasonality: true,
    weekly_seasonality: true,
    yearly_seasonality: true,
    changepoint_range: 0.8,
    changepoint_prior_scale: 0.05,
    seasonality_mode: ProphetSeasonalityModeEnum.ADDITIVE
});

const DEFAULT_ITRANSFORMER_FORM_DATA = (realm: string): ITransformerModelConfig => ({
    ...BASE_FORM_DEFAULTS,
    realm,
    type: ModelTypeEnum.ITRANSFORMER,
    seq_len: 96,
    d_model: 128,
    n_heads: 4,
    n_layers: 2,
    d_ff: 256,
    dropout: 0.1,
    epochs: 30,
    batch_size: 64,
    lr: 0.001,
    val_split: 0.2
});

const DEFAULT_NL_ENERGY_FORECASTER_FORM_DATA = (realm: string): NLEnergyForecasterModelConfig => ({
    ...BASE_FORM_DEFAULTS,
    realm,
    type: ModelTypeEnum.NL_ENERGY_FORECASTER,
    forecast_periods: 24,
    forecast_frequency: '1h',
    feature_mapping: {
        temperature_2m: '',
        cloud_cover: '',
        wind_speed_10m: '',
        shortwave_radiation: '',
        total_load: '',
        generation_forecast: '',
        Open: '',
        High: '',
        Low: '',
        'Change %': ''
    }
});

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

            .attribute-row {
                align-items: center;
            }

            .select-attr {
                flex: none;
                min-width: 125px;
            }

            .selected-attr {
                display: flex;
                align-items: center;
                padding: 0 16px 0 8px;
                gap: 8px;
                cursor: pointer;
            }

            .selected-attr or-icon {
                --or-icon-width: 20px;
                --or-icon-height: 20px;
                flex-shrink: 0;
            }

            .selected-attr-text {
                display: flex;
                flex-direction: column;
                min-width: 0;
            }

            .selected-attr-text > span {
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
            }

            .selected-attr-text > span:first-child {
                font-weight: 500;
            }

            .selected-attr-text > span:last-child {
                font-size: 0.9em;
                opacity: 0.7;
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
    protected loading: boolean = true;

    @state()
    protected isValid: boolean = false;

    @state()
    protected modified: boolean = false;

    @state()
    protected error: string | null = null;

    @state()
    protected targetAsset: Asset | null = null;

    @state()
    protected regressorAssets: Map<number, Asset> = new Map();

    protected readonly rootPath = getRootPath();

    @state()
    protected formData: ModelConfig = DEFAULT_PROPHET_FORM_DATA('');

    // Handle basic form field updates
    protected handleBasicInput(ev: OrInputChangedEvent | CustomEvent<{ value: string }>) {
        const value = 'detail' in ev ? ev.detail?.value : undefined;
        const target = ev.target as HTMLInputElement;

        if (!target || value === undefined) {
            return;
        }

        if (target.name === 'type') {
            const newType = value as ModelTypeEnum;
            if (newType === ModelTypeEnum.ITRANSFORMER) {
                this.formData = { ...DEFAULT_ITRANSFORMER_FORM_DATA(this.realm), name: this.formData.name, target: this.formData.target };
            } else if (newType === ModelTypeEnum.NL_ENERGY_FORECASTER) {
                this.formData = { ...DEFAULT_NL_ENERGY_FORECASTER_FORM_DATA(this.realm), name: this.formData.name, target: this.formData.target };
            } else {
                this.formData = { ...DEFAULT_PROPHET_FORM_DATA(this.realm), name: this.formData.name, target: this.formData.target };
            }
            return;
        }

        this.formData = {
            ...this.formData,
            [target.name]: value
        };
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

        if (!target || value === undefined || !this.formData.regressors) {
            return;
        }

        this.formData.regressors[index] = {
            ...this.formData.regressors[index],
            [target.name]: value
        };
        this.requestUpdate();
    }

    // Load asset data for target
    protected async loadTargetAsset() {
        if (this.formData.target.asset_id && this.formData.target.attribute_name) {
            try {
                const response = await manager.rest.api.AssetResource.get(this.formData.target.asset_id);
                this.targetAsset = response.data;
            } catch (err) {
                console.error('Failed to load target asset:', err);
                this.targetAsset = null;
            }
        } else {
            this.targetAsset = null;
        }
    }

    // Open dialog to select target attribute
    protected openTargetDialog() {
        const currentSelection =
            this.formData.target.asset_id && this.formData.target.attribute_name
                ? [{ id: this.formData.target.asset_id, name: this.formData.target.attribute_name }]
                : [];

        // disable scrolling
        document.body.style.overflow = 'hidden';

        const dialog = showDialog(
            new CustomAssetAttributePicker().setShowOnlyDatapointAttrs(true).setMultiSelect(false).setSelectedAttributes(currentSelection)
        );

        // restore scrolling
        const restoreScroll = () => {
            document.body.style.overflow = '';
        };

        dialog.addEventListener(OrAssetAttributePickerPickedEvent.NAME, async (ev: OrAssetAttributePickerPickedEvent) => {
            const selected = ev.detail[0];
            if (selected) {
                this.formData = {
                    ...this.formData,
                    target: {
                        ...this.formData.target,
                        asset_id: selected.id,
                        attribute_name: selected.name
                    }
                };
                await this.loadTargetAsset();
                this.requestUpdate();
            }
            restoreScroll();
        });

        dialog.addEventListener('or-mwc-dialog-closed', restoreScroll);
    }

    // Load asset data for regressor
    protected async loadRegressorAsset(index: number) {
        if (!this.formData.regressors) return;

        const regressor = this.formData.regressors[index];
        if (regressor.asset_id && regressor.attribute_name) {
            try {
                const response = await manager.rest.api.AssetResource.get(regressor.asset_id);
                this.regressorAssets.set(index, response.data);
                this.regressorAssets = new Map(this.regressorAssets);
            } catch (err) {
                console.error('Failed to load regressor asset:', err);
                this.regressorAssets.delete(index);
                this.regressorAssets = new Map(this.regressorAssets);
            }
        }
    }

    // Open dialog to select regressor attribute
    protected openRegressorDialog(index: number) {
        if (!this.formData.regressors) {
            return;
        }

        const regressor = this.formData.regressors[index];
        const currentSelection =
            regressor.asset_id && regressor.attribute_name ? [{ id: regressor.asset_id, name: regressor.attribute_name }] : [];

        document.body.style.overflow = 'hidden';

        const dialog = showDialog(
            new CustomAssetAttributePicker()
                .setShowOnlyHasPredictedDatapointsAttrs(true) // has future datapoints
                .setShowOnlyDatapointAttrs(true) // has past datapoints
                .setMultiSelect(false)
                .setSelectedAttributes(currentSelection)
        );

        const restoreScroll = () => {
            document.body.style.overflow = '';
        };

        dialog.addEventListener(OrAssetAttributePickerPickedEvent.NAME, async (ev: OrAssetAttributePickerPickedEvent) => {
            const selected = ev.detail[0];
            if (selected && this.formData.regressors) {
                this.formData.regressors[index] = {
                    ...this.formData.regressors[index],
                    asset_id: selected.id,
                    attribute_name: selected.name
                };
                await this.loadRegressorAsset(index);
                this.requestUpdate();
            }
            restoreScroll();
        });

        dialog.addEventListener('or-mwc-dialog-closed', restoreScroll);
    }

    willUpdate(): void {
        this.isValid = this.isFormValid();
        this.modified = this.isFormModified();
    }

    // Set up all the data for the editor
    protected async setupEditor() {
        this.formData = DEFAULT_PROPHET_FORM_DATA(this.realm);
        await this.loadConfig();
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
            this.formData = structuredClone(this.modelConfig);

            // Load asset data for displaying
            await this.loadTargetAsset();
            if (this.formData.regressors) {
                for (let i = 0; i < this.formData.regressors.length; i++) {
                    await this.loadRegressorAsset(i);
                }
            }

            this.loading = false;
            return;
        } catch (err) {
            this.loading = false;
            console.error('Failed to load config:', err);
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
            console.error('Failed to save config:', error);
            showSnackbar(undefined, 'Failed to save the config');
        }
    }

    // Check form for validity
    isFormValid() {
        // check target properties
        if (!this.formData.target.asset_id || !this.formData.target.attribute_name) {
            return false;
        }

        // check all regressors
        if (this.formData.regressors) {
            for (const regressor of this.formData.regressors) {
                if (!regressor.asset_id || !regressor.attribute_name) {
                    return false;
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

    // Handle adding a regressor
    handleAddRegressor() {
        this.formData.regressors = this.formData.regressors ?? [];

        this.formData.regressors.push({
            asset_id: '',
            attribute_name: '',
            training_data_period: 'P6M'
        });
        this.requestUpdate();
    }

    // Handle deleting a regressor
    handleDeleteRegressor(index: number) {
        if (!this.formData.regressors) {
            return;
        }

        this.formData.regressors.splice(index, 1);

        // Clean up regressors if all are deleted
        if (this.formData.regressors?.length === 0) {
            this.formData.regressors = null;
        }

        this.requestUpdate();
    }

    // Get the regressor template
    getRegressorTemplate(index: number) {
        if (!this.formData.regressors) {
            return;
        }

        const regressor = this.formData.regressors[index];
        return html`
            <or-panel heading="REGRESSOR ${index + 1}">
                <div class="column">
                    <div class="row attribute-row">
                        ${when(
                            regressor.asset_id && regressor.attribute_name && this.regressorAssets.has(index),
                            () => {
                                const asset = this.regressorAssets.get(index)!;
                                const attribute = asset.attributes?.[regressor.attribute_name];
                                const descriptors = attribute
                                    ? AssetModelUtil.getAttributeAndValueDescriptors(asset.type, regressor.attribute_name, attribute)
                                    : [];
                                const label = attribute
                                    ? Util.getAttributeLabel(attribute, descriptors[0], asset.type, true)
                                    : regressor.attribute_name;
                                return html`
                                    <div class="selected-attr" @click="${() => this.openRegressorDialog(index)}">
                                        ${getAssetDescriptorIconTemplate(AssetModelUtil.getAssetDescriptor(asset.type))}
                                        <div class="selected-attr-text">
                                            <span>${asset.name}</span>
                                            <span>${label}</span>
                                        </div>
                                    </div>
                                `;
                            },
                            () => html`
                                <or-mwc-input
                                    class="select-attr"
                                    type="${InputType.BUTTON}"
                                    icon="magnify"
                                    label="Select regressor"
                                    @or-mwc-input-changed="${() => this.openRegressorDialog(index)}"
                                ></or-mwc-input>
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
                                .options="${[['prophet', 'Prophet'], ['itransformer', 'iTransformer'], ['nl_energy_forecaster', 'NL Energy Forecaster']]}"
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
                        <div class="row attribute-row">
                            ${when(
                                this.formData.target.asset_id && this.formData.target.attribute_name && this.targetAsset,
                                () => {
                                    const attribute = this.targetAsset!.attributes?.[this.formData.target.attribute_name];
                                    const descriptors = attribute
                                        ? AssetModelUtil.getAttributeAndValueDescriptors(
                                              this.targetAsset!.type,
                                              this.formData.target.attribute_name,
                                              attribute
                                          )
                                        : [];
                                    const label = attribute
                                        ? Util.getAttributeLabel(attribute, descriptors[0], this.targetAsset!.type, true)
                                        : this.formData.target.attribute_name;
                                    return html`
                                        <div class="selected-attr" @click="${this.openTargetDialog}">
                                            ${getAssetDescriptorIconTemplate(AssetModelUtil.getAssetDescriptor(this.targetAsset!.type))}
                                            <div class="selected-attr-text">
                                                <span>${this.targetAsset!.name}</span>
                                                <span>${label}</span>
                                            </div>
                                        </div>
                                    `;
                                },
                                () => html`
                                    <or-mwc-input
                                        class="select-attr"
                                        type="${InputType.BUTTON}"
                                        icon="magnify"
                                        label="Select target"
                                        @click="${this.openTargetDialog}"
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

                <!-- Model parameters — dynamic based on model type -->
                <or-panel heading="PARAMETERS">
                    <div class="column">
                        ${this.formData.type === ModelTypeEnum.NL_ENERGY_FORECASTER
                            ? (() => {
                                const n = this.formData as NLEnergyForecasterModelConfig;
                                return html`
                                    <div class="row">
                                        <p style="margin:0;opacity:0.7;font-size:0.9em;">
                                            Pre-trained model (Nazim112/nl-energy-forecaster).
                                            Map each feature column to a regressor in the format
                                            <em>asset_id.attribute_name</em>.
                                        </p>
                                    </div>
                                    <div class="row">
                                        <or-mwc-input
                                            style="flex:1;max-width:100%;"
                                            type="${InputType.TEXTAREA}"
                                            name="feature_mapping"
                                            @or-mwc-input-changed="${(e: OrInputChangedEvent) => {
                                                try {
                                                    this.formData = { ...(this.formData as NLEnergyForecasterModelConfig), feature_mapping: JSON.parse(e.detail?.value ?? '{}') };
                                                } catch (_) { /* ignore invalid JSON while typing */ }
                                            }}"
                                            label="Feature mapping (JSON)"
                                            .value="${JSON.stringify(n.feature_mapping, null, 2)}"
                                            rows="14"
                                            required
                                        ></or-mwc-input>
                                    </div>
                                `;
                              })()
                            : ''}
                        ${when(
                            this.formData.type === ModelTypeEnum.PROPHET,
                            () => {
                                const p = this.formData as ProphetModelConfig;
                                return html`
                                    <div class="row">
                                        <or-mwc-input
                                            type="${InputType.NUMBER}"
                                            name="changepoint_range"
                                            @or-mwc-input-changed="${this.handleBasicInput}"
                                            label="Changepoint range"
                                            .value="${p.changepoint_range}"
                                            max="1.0"
                                            min="0.0"
                                            step="0.01"
                                            required
                                        ></or-mwc-input>
                                        <or-mwc-input
                                            type="${InputType.NUMBER}"
                                            name="changepoint_prior_scale"
                                            @or-mwc-input-changed="${this.handleBasicInput}"
                                            label="Changepoint prior scale"
                                            .value="${p.changepoint_prior_scale}"
                                            max="1.0"
                                            min="0.0"
                                            step="0.01"
                                            required
                                        ></or-mwc-input>
                                    </div>
                                    <div class="row">
                                        <or-mwc-input
                                            type="${InputType.SELECT}"
                                            .options="${[
                                                [ProphetSeasonalityModeEnum.ADDITIVE, 'Additive'],
                                                [ProphetSeasonalityModeEnum.MULTIPLICATIVE, 'Multiplicative']
                                            ]}"
                                            name="seasonality_mode"
                                            @or-mwc-input-changed="${this.handleBasicInput}"
                                            label="Seasonality mode"
                                            .value="${p.seasonality_mode}"
                                            required
                                        ></or-mwc-input>
                                        <or-mwc-input
                                            type="${InputType.CHECKBOX}"
                                            name="daily_seasonality"
                                            @or-mwc-input-changed="${this.handleBasicInput}"
                                            label="Daily seasonality"
                                            .value="${p.daily_seasonality}"
                                        ></or-mwc-input>
                                        <or-mwc-input
                                            type="${InputType.CHECKBOX}"
                                            name="weekly_seasonality"
                                            @or-mwc-input-changed="${this.handleBasicInput}"
                                            label="Weekly seasonality"
                                            .value="${p.weekly_seasonality}"
                                        ></or-mwc-input>
                                        <or-mwc-input
                                            type="${InputType.CHECKBOX}"
                                            name="yearly_seasonality"
                                            @or-mwc-input-changed="${this.handleBasicInput}"
                                            label="Yearly seasonality"
                                            .value="${p.yearly_seasonality}"
                                        ></or-mwc-input>
                                    </div>
                                `;
                            },
                            () => {
                                if (this.formData.type !== ModelTypeEnum.ITRANSFORMER) return html``;
                                const t = this.formData as ITransformerModelConfig;
                                return html`
                                    <div class="row">
                                        <or-mwc-input
                                            type="${InputType.NUMBER}"
                                            name="seq_len"
                                            @or-mwc-input-changed="${this.handleBasicInput}"
                                            label="Lookback window (seq len)"
                                            .value="${t.seq_len}"
                                            min="2"
                                            required
                                        ></or-mwc-input>
                                        <or-mwc-input
                                            type="${InputType.NUMBER}"
                                            name="epochs"
                                            @or-mwc-input-changed="${this.handleBasicInput}"
                                            label="Training epochs"
                                            .value="${t.epochs}"
                                            min="1"
                                            required
                                        ></or-mwc-input>
                                    </div>
                                    <div class="row">
                                        <or-mwc-input
                                            type="${InputType.NUMBER}"
                                            name="d_model"
                                            @or-mwc-input-changed="${this.handleBasicInput}"
                                            label="Embedding dimension"
                                            .value="${t.d_model}"
                                            min="1"
                                            required
                                        ></or-mwc-input>
                                        <or-mwc-input
                                            type="${InputType.NUMBER}"
                                            name="n_heads"
                                            @or-mwc-input-changed="${this.handleBasicInput}"
                                            label="Attention heads"
                                            .value="${t.n_heads}"
                                            min="1"
                                            required
                                        ></or-mwc-input>
                                        <or-mwc-input
                                            type="${InputType.NUMBER}"
                                            name="n_layers"
                                            @or-mwc-input-changed="${this.handleBasicInput}"
                                            label="Encoder layers"
                                            .value="${t.n_layers}"
                                            min="1"
                                            required
                                        ></or-mwc-input>
                                        <or-mwc-input
                                            type="${InputType.NUMBER}"
                                            name="d_ff"
                                            @or-mwc-input-changed="${this.handleBasicInput}"
                                            label="Feed-forward dimension"
                                            .value="${t.d_ff}"
                                            min="1"
                                            required
                                        ></or-mwc-input>
                                    </div>
                                    <div class="row">
                                        <or-mwc-input
                                            type="${InputType.NUMBER}"
                                            name="batch_size"
                                            @or-mwc-input-changed="${this.handleBasicInput}"
                                            label="Batch size"
                                            .value="${t.batch_size}"
                                            min="1"
                                            required
                                        ></or-mwc-input>
                                        <or-mwc-input
                                            type="${InputType.NUMBER}"
                                            name="lr"
                                            @or-mwc-input-changed="${this.handleBasicInput}"
                                            label="Learning rate"
                                            .value="${t.lr}"
                                            min="0"
                                            step="0.0001"
                                            required
                                        ></or-mwc-input>
                                        <or-mwc-input
                                            type="${InputType.NUMBER}"
                                            name="dropout"
                                            @or-mwc-input-changed="${this.handleBasicInput}"
                                            label="Dropout"
                                            .value="${t.dropout}"
                                            min="0.0"
                                            max="1.0"
                                            step="0.01"
                                            required
                                        ></or-mwc-input>
                                        <or-mwc-input
                                            type="${InputType.NUMBER}"
                                            name="val_split"
                                            @or-mwc-input-changed="${this.handleBasicInput}"
                                            label="Validation split"
                                            .value="${t.val_split}"
                                            min="0.0"
                                            max="0.99"
                                            step="0.05"
                                            required
                                        ></or-mwc-input>
                                    </div>
                                `;
                            }
                        )}
                    </div>
                </or-panel>
                <hr />
                <!-- Regressors -->
                ${when(
                    this.formData.regressors,
                    () => map(this.formData.regressors ?? [], (_regressor, index) => this.getRegressorTemplate(index)),
                    () => html``
                )}
                ${this.getAddRegressorTemplate()}
            </form>
        `;
    }
}
