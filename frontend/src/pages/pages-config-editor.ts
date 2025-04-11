/* eslint-disable @typescript-eslint/no-unused-vars */
import { css, html, LitElement, PropertyValues } from 'lit'
import { customElement, property, state } from 'lit/decorators.js'
import { ModelTypeEnum, ProphetSeasonalityModeEnum } from '../services/models'
import type { ProphetModelConfig } from '../services/models'
import { ApiService } from '../services/api-service'
import { Router, RouterLocation } from '@vaadin/router'
import '@openremote/or-icon'
import '@openremote/or-panel'
import { InputType, OrInputChangedEvent } from '@openremote/or-mwc-components/or-mwc-input'
import '../components/loading-spinner'
import { showSnackbar } from '@openremote/or-mwc-components/or-mwc-snackbar'
import { getRealm } from '../util'

enum TimeDurationUnit {
    MINUTE = 'M',
    HOUR = 'H'
}

enum PandasTimeUnit {
    MINUTE = 'min',
    HOUR = 'h'
}

@customElement('page-config-viewer')
export class PageConfigViewer extends LitElement {
    static get styles() {
        return css`
            :host {
                --or-panel-background-color: #fff;
                --or-panel-heading-text-transform: uppercase;
                --or-panel-heading-color: var(--or-app-color3);
                --or-panel-heading-font-size: 14px;
            }

            .config-viewer {
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

            .column {
                display: flex;
                flex-direction: column;
                flex: 1 1 0;
                gap: 20px;
                padding: 10px 0px;
            }

            or-mwc-input {
                flex: 1;
                max-width: 300px;
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
        `
    }

    @property({ type: String })
    configId?: string

    @state()
    private modelConfig: ProphetModelConfig | null = null

    // <assetId, assetName>
    @state()
    private assetSelectList: Map<string, string> = new Map()

    // assetId -> <attributeName, attributeName>
    @state()
    private attributeSelectList: Map<string, Map<string, string>> = new Map()

    private assetSearchSize: number = 10

    @state()
    private loading: boolean = true

    @state()
    private isValid: boolean = false

    @state()
    private modified: boolean = false

    private readonly apiService: ApiService = new ApiService()

    @state()
    private formData: ProphetModelConfig = {
        type: ModelTypeEnum.PROPHET,
        realm: getRealm(),
        name: '',
        enabled: true,
        target: {
            asset_id: '',
            attribute_name: '',
            cutoff_timestamp: new Date().getTime()
        },
        forecast_interval: 'PT1H',
        forecast_periods: 48,
        forecast_frequency: '1h',
        training_interval: 'PT24H',
        changepoint_range: 0.8,
        changepoint_prior_scale: 0.05,
        seasonality_mode: ProphetSeasonalityModeEnum.ADDITIVE
    }

    // Update lifecycle
    updated(_changedProperties: PropertyValues) {
        this.isValid = this.isFormValid()
        this.modified = this.isFormModified()
    }

    // Set up all the data for the editor
    private async setupEditor() {
        await this.loadAssets()
        await this.loadConfig()
    }

    // Loads valid assets and their attributes from the API
    private async loadAssets() {
        this.assetSelectList.clear()
        const assets = await this.apiService.getAssets()
        assets.forEach((asset) => {
            this.assetSelectList.set(asset.id, asset.name)

            // attributes: { [key: string]: AssetAttribute };
            this.attributeSelectList.set(asset.id, new Map(Object.entries(asset.attributes).map(([key, value]) => [key, value.name])))
        })
    }

    // Try to load the config from the API
    private async loadConfig() {
        this.loading = true
        this.isValid = false

        if (!this.configId) {
            this.loading = false
            return
        }
        try {
            this.modelConfig = await this.apiService.getModelConfig(this.configId)
            // Update the form data with the loaded config
            this.formData = this.modelConfig
            this.loading = false
            return
        } catch (err) {
            this.loading = false
            console.error(err)
        }
    }

    // Extract the number from the ISO 8601 Duration string
    getNumberFromDuration(duration: string): number | null {
        const match = /PT(\d+)([HM])/.exec(duration)
        return match ? parseInt(match[1], 10) : null
    }

    // Extract the unit from the ISO 8601 Duration string
    getUnitFromDuration(duration: string): string | null {
        const match = /PT(\d+)([HM])/.exec(duration)
        return match ? match[2] : null
    }

    // Extract the number from the Pandas Offset string
    getNumberFromPandasOffset(offset: string): number | null {
        const match = /(\d+)(min|h)/.exec(offset)
        return match ? parseInt(match[1], 10) : null
    }

    // Extract the unit from the Pandas Offset string
    getUnitFromPandasOffset(offset: string): string | null {
        const match = /(\d+)(min|h)/.exec(offset)
        return match ? match[2] : null
    }

    // Handle the Vaadin Router location change event
    onAfterEnter(location: RouterLocation) {
        this.configId = location.params.id as string
        return this.setupEditor()
    }

    // Generic input handler
    onInput(ev: OrInputChangedEvent) {
        const value: string | boolean | number | undefined = ev.detail?.value
        const target = ev.target as HTMLInputElement

        if (!target || value === undefined) {
            return
        }
        const name = target.name

        this.formData = {
            ...this.formData,
            [name]: value
        }
    }

    // Handle checkbox inputs
    onCheckboxInput(ev: OrInputChangedEvent) {
        const value: boolean = ev.detail?.value
        const target = ev.target as HTMLInputElement

        this.formData = {
            ...this.formData,
            [target.name]: value
        }
    }

    // Handle target input (nested property)
    onTargetInput(ev: OrInputChangedEvent, isAssetIdChange: boolean = false) {
        const value: string | number | undefined = ev.detail?.value
        const target = ev.target as HTMLInputElement

        if (!target || value === undefined) {
            return
        }

        const key = target.name.split('.')[1]
        if (!key) {
            console.error('Invalid target input name:', target.name)
            return
        }

        if (isAssetIdChange) {
            // set attribute to first attribute
            this.formData.target.attribute_name =
                this.attributeSelectList
                    .get(value as string)
                    ?.values()
                    .next().value ?? ''
        }

        this.formData = {
            ...this.formData,
            target: {
                ...this.formData.target,
                [key]: value
            }
        }
    }

    // Handle the save button click
    async onSave() {
        const isExistingConfig = this.modelConfig !== null

        // Switch between update and create -- based on whether the config
        const saveRequest = isExistingConfig
            ? this.apiService.updateModelConfig(this.formData)
            : this.apiService.createModelConfig(this.formData)

        try {
            const modelConfig = await saveRequest
            if (isExistingConfig) {
                await this.loadConfig()
            } else {
                Router.go(`${modelConfig.realm}/configs/${modelConfig.id}`)
            }
        } catch (error) {
            console.error(error)
            showSnackbar(undefined, 'Failed to save the config')
        }
    }

    // Check form for validity
    isFormValid() {
        const inputs = this.shadowRoot?.querySelectorAll('or-mwc-input') as NodeListOf<HTMLInputElement>
        if (inputs) {
            return Array.from(inputs).every((input) => input.checkValidity())
        }
        return false
    }

    // Check if the form has been modified
    isFormModified() {
        return JSON.stringify(this.formData) !== JSON.stringify(this.modelConfig)
    }

    // Handle adding a regressor
    handleAddRegressor() {
        // TODO: Implement this
        console.log('add regressor')
    }

    // Search provider for the asset select list
    protected async searchAssets(search?: string): Promise<[any, string][]> {
        const options = [...this.assetSelectList.entries()]
        if (!search) {
            return options.slice(0, this.assetSearchSize)
        }
        const searchTerm = search.toLowerCase()
        return options.filter(([_value, label]) => label.toLowerCase().includes(searchTerm)).slice(0, this.assetSearchSize)
    }

    // Render the editor
    protected render() {
        if (this.loading) {
            return html`<loading-spinner></loading-spinner>`
        }

        return html`
            <form id="config-form" class="config-viewer">
                <div class="config-header">
                    <div class="config-header-name">
                        <or-mwc-input
                            name="name"
                            focused
                            outlined
                            type="${InputType.TEXT}"
                            label="Model Name"
                            @or-mwc-input-changed="${(e: OrInputChangedEvent) => this.onInput(e)}"
                            .value="${this.formData.name}"
                            required
                            minlength="1"
                            maxlength="255"
                        ></or-mwc-input>

                        <or-mwc-input
                            type="${InputType.CHECKBOX}"
                            name="enabled"
                            @or-mwc-input-changed="${(e: OrInputChangedEvent) => this.onCheckboxInput(e)}"
                            label="Enabled"
                            .value="${this.formData.enabled}"
                        ></or-mwc-input>
                    </div>

                    <!-- Note: I know this is odd, but the disable state would not update properly via the disabled/.disabled/?disabled attribute -->
                    <div class="config-header-controls">
                        ${this.isValid && this.modified
                            ? html`<or-mwc-input
                                  type="${InputType.BUTTON}"
                                  id="save-btn"
                                  label="save"
                                  raised
                                  @click="${this.onSave}"
                              ></or-mwc-input>`
                            : html`<or-mwc-input type="${InputType.BUTTON}" id="save-btn" label="save" raised disabled></or-mwc-input>`}
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
                                @or-mwc-input-changed="${(e: OrInputChangedEvent) => this.onInput(e)}"
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
                            <or-mwc-input
                                type="${InputType.TEXT}"
                                name="forecast_interval"
                                @or-mwc-input-changed="${(e: OrInputChangedEvent) => this.onInput(e)}"
                                label="Generate new forecast every"
                                .value="${this.formData.forecast_interval}"
                                required
                            ></or-mwc-input>
                        </div>

                        <div class="row">
                            <!-- forecast_periods -->
                            <or-mwc-input
                                type="${InputType.NUMBER}"
                                name="forecast_periods"
                                @or-mwc-input-changed="${(e: OrInputChangedEvent) => this.onInput(e)}"
                                label="Forecasted datapoints"
                                .value="${this.formData.forecast_periods}"
                                required
                            ></or-mwc-input>

                            <or-mwc-input
                                type="${InputType.TEXT}"
                                name="forecast_frequency"
                                @or-mwc-input-changed="${(e: OrInputChangedEvent) => this.onInput(e)}"
                                label="Time between datapoints"
                                .value="${this.formData.forecast_frequency}"
                                required
                            ></or-mwc-input>
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
                                @or-mwc-input-changed="${(e: OrInputChangedEvent) => this.onTargetInput(e, true)}"
                                label="Asset"
                                .value="${this.formData.target.asset_id}"
                                .options="${[...this.assetSelectList.entries()].slice(0, this.assetSearchSize)}"
                                .searchProvider="${this.searchAssets.bind(this)}"
                            ></or-mwc-input>

                            <or-mwc-input
                                type="${InputType.SELECT}"
                                name="target.attribute_name"
                                @or-mwc-input-changed="${(e: OrInputChangedEvent) => this.onTargetInput(e)}"
                                label="Attribute"
                                .value="${this.formData.target.attribute_name}"
                                .options="${[...(this.attributeSelectList.get(this.formData.target.asset_id) ?? new Map())]}"
                            ></or-mwc-input>

                            <or-mwc-input
                                type="${InputType.DATETIME}"
                                name="target.cutoff_timestamp"
                                @or-mwc-input-changed="${(e: OrInputChangedEvent) => this.onTargetInput(e)}"
                                label="Use datapoints since"
                                .value="${this.formData.target.cutoff_timestamp}"
                                required
                            ></or-mwc-input>
                        </div>
                    </div>
                </or-panel>

                <!-- Model training, e.g the schedule-->
                <or-panel heading="MODEL TRAINING">
                    <div class="column">
                        <div class="row">
                            <or-mwc-input
                                type="${InputType.TEXT}"
                                name="training_interval"
                                @or-mwc-input-changed="${(e: OrInputChangedEvent) => this.onInput(e)}"
                                label="Training interval"
                                .value="${this.formData.training_interval}"
                                required
                            ></or-mwc-input>
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
                                @or-mwc-input-changed="${(e: OrInputChangedEvent) => this.onInput(e)}"
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
                                @or-mwc-input-changed="${(e: OrInputChangedEvent) => this.onInput(e)}"
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
                                @or-mwc-input-changed="${(e: OrInputChangedEvent) => this.onInput(e)}"
                                label="Seasonality mode"
                                .value="${this.formData.seasonality_mode}"
                                required
                            ></or-mwc-input>
                            <!-- daily_seasonality -->
                            <or-mwc-input
                                type="${InputType.CHECKBOX}"
                                name="daily_seasonality"
                                @or-mwc-input-changed="${(e: OrInputChangedEvent) => this.onCheckboxInput(e)}"
                                label="Daily seasonality"
                                .value="${this.formData.daily_seasonality}"
                            ></or-mwc-input>
                            <!-- weekly_seasonality -->
                            <or-mwc-input
                                type="${InputType.CHECKBOX}"
                                name="weekly_seasonality"
                                @or-mwc-input-changed="${(e: OrInputChangedEvent) => this.onCheckboxInput(e)}"
                                label="Weekly seasonality"
                                .value="${this.formData.weekly_seasonality}"
                            ></or-mwc-input>
                            <!-- yearly_seasonality -->
                            <or-mwc-input
                                type="${InputType.CHECKBOX}"
                                name="yearly_seasonality"
                                @or-mwc-input-changed="${(e: OrInputChangedEvent) => this.onCheckboxInput(e)}"
                                label="Yearly seasonality"
                                .value="${this.formData.yearly_seasonality}"
                            ></or-mwc-input>
                        </div>
                    </div>
                </or-panel>

                <!-- Regressors, these will be dynamic based on the model type -->
                <or-panel heading="REGRESSOR">
                    <div class="column">
                        <div class="row">
                            <or-mwc-input
                                type="${InputType.BUTTON}"
                                icon="plus"
                                label="add regressor"
                                @click="${this.handleAddRegressor}"
                            ></or-mwc-input>
                        </div>
                    </div>
                </or-panel>
            </form>
        `
    }
}
