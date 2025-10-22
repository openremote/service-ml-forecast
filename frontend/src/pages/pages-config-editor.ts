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
import type { ProphetModelConfig } from '../services/models';
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
import { AssetModelUtil } from '@openremote/model';

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
    protected modelConfig: ProphetModelConfig | null = null;

    @state()
    protected loading: boolean = true;

    @state()
    protected isValid: boolean = false;

    @state()
    protected modified: boolean = false;

    @state()
    protected error: string | null = null;

    @state()
    protected targetAsset: any = null;

    @state()
    protected regressorAssets: Map<number, any> = new Map();

    protected readonly rootPath = getRootPath();

    @state()
    protected formData: ProphetModelConfig = {
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
        training_interval: 'PT1H',
        daily_seasonality: true,
        weekly_seasonality: true,
        yearly_seasonality: true,
        changepoint_range: 0.8,
        changepoint_prior_scale: 0.05,
        seasonality_mode: ProphetSeasonalityModeEnum.ADDITIVE
    };

    // Handle basic form field updates
    protected handleBasicInput(ev: OrInputChangedEvent | CustomEvent<{ value: string }>) {
        const value = 'detail' in ev ? ev.detail?.value : undefined;
        const target = ev.target as HTMLInputElement;

        if (!target || value === undefined) {
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
                console.error(err);
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

        dialog.addEventListener(OrAssetAttributePickerPickedEvent.NAME, async (ev: any) => {
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
                console.error(err);
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

        dialog.addEventListener(OrAssetAttributePickerPickedEvent.NAME, async (ev: any) => {
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
        this.formData.realm = this.realm;
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
                                const asset = this.regressorAssets.get(index);
                                const attribute = asset?.attributes?.[regressor.attribute_name];
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
                                    @click="${() => this.openRegressorDialog(index)}"
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
                                .options="${[['prophet', 'Prophet']]}"
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
                                    const attribute = this.targetAsset.attributes?.[this.formData.target.attribute_name];
                                    const descriptors = attribute
                                        ? AssetModelUtil.getAttributeAndValueDescriptors(
                                              this.targetAsset.type,
                                              this.formData.target.attribute_name,
                                              attribute
                                          )
                                        : [];
                                    const label = attribute
                                        ? Util.getAttributeLabel(attribute, descriptors[0], this.targetAsset.type, true)
                                        : this.formData.target.attribute_name;
                                    return html`
                                        <div class="selected-attr" @click="${this.openTargetDialog}">
                                            ${getAssetDescriptorIconTemplate(AssetModelUtil.getAssetDescriptor(this.targetAsset.type))}
                                            <div class="selected-attr-text">
                                                <span>${this.targetAsset.name}</span>
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

                <!-- Model training, e.g the schedule-->
                <or-panel heading="MODEL TRAINING">
                    <div class="column">
                        <div class="row">
                            <!-- Training interval (ISO 8601) -->
                            <custom-duration-input
                                name="training_interval"
                                .type="${DurationInputType.ISO_8601}"
                                @value-changed="${this.handleBasicInput}"
                                label="Train model every"
                                .value="${this.formData.training_interval}"
                            ></custom-duration-input>
                        </div>
                    </div>
                </or-panel>

                <!-- Model parameters, these will be dynamic based on the model type -->
                <or-panel heading="PARAMETERS">
                    <div class="column">
                        <div class="row">
                            <!-- changepoint_range -->
                            <or-mwc-input
                                type="${InputType.NUMBER}"
                                name="changepoint_range"
                                @or-mwc-input-changed="${this.handleBasicInput}"
                                label="Changepoint range"
                                .value="${this.formData.changepoint_range}"
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
                                .value="${this.formData.changepoint_prior_scale}"
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
                                .value="${this.formData.seasonality_mode}"
                                required
                            ></or-mwc-input>
                            <!-- daily_seasonality -->
                            <or-mwc-input
                                type="${InputType.CHECKBOX}"
                                name="daily_seasonality"
                                @or-mwc-input-changed="${this.handleBasicInput}"
                                label="Daily seasonality"
                                .value="${this.formData.daily_seasonality}"
                            ></or-mwc-input>
                            <!-- weekly_seasonality -->
                            <or-mwc-input
                                type="${InputType.CHECKBOX}"
                                name="weekly_seasonality"
                                @or-mwc-input-changed="${this.handleBasicInput}"
                                label="Weekly seasonality"
                                .value="${this.formData.weekly_seasonality}"
                            ></or-mwc-input>
                            <!-- yearly_seasonality -->
                            <or-mwc-input
                                type="${InputType.CHECKBOX}"
                                name="yearly_seasonality"
                                @or-mwc-input-changed="${this.handleBasicInput}"
                                label="Yearly seasonality"
                                .value="${this.formData.yearly_seasonality}"
                            ></or-mwc-input>
                        </div>
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
