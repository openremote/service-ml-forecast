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
import '../components/custom-duration-input'
import { DurationInputType } from '../components/custom-duration-input'

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

            hr {
                border: 0;
                height: 1px;
                background-color: var(--or-app-color5);
                margin: 5px 0;
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
        `
    }

    @property({ type: String })
    configId?: string

    @state()
    private modelConfig: ProphetModelConfig | null = null

    @state()
    private assetSelectList: Map<string, string> = new Map()

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
        name: 'New Model Config',
        enabled: true,
        target: {
            asset_id: '',
            attribute_name: '',
            cutoff_timestamp: new Date().getTime()
        },
        regressors: null,
        forecast_interval: 'PT1H',
        forecast_periods: 24,
        forecast_frequency: '1h',
        training_interval: 'PT24H',
        changepoint_range: 0.8,
        changepoint_prior_scale: 0.05,
        seasonality_mode: ProphetSeasonalityModeEnum.ADDITIVE
    }

    // Handle basic form field updates
    private handleBasicInput(ev: OrInputChangedEvent | CustomEvent<{ value: string }>) {
        const value = 'detail' in ev ? ev.detail?.value : undefined
        const target = ev.target as HTMLInputElement

        if (!target || value === undefined) {
            return
        }

        this.formData = {
            ...this.formData,
            [target.name]: value
        }
    }

    // Handle target-specific updates
    private handleTargetInput(ev: OrInputChangedEvent) {
        const value = ev.detail?.value
        const target = ev.target as HTMLInputElement

        if (!target || value === undefined) {
            return
        }

        const [, field] = target.name.split('.')
        if (!field) {
            console.error('Invalid target input name:', target.name)
            return
        }

        // Auto-select first attribute when asset changes
        if (field === 'asset_id') {
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
                [field]: value
            }
        }
    }

    // Handle regressor-specific updates
    private handleRegressorInput(ev: OrInputChangedEvent, index: number) {
        const value = ev.detail?.value
        const target = ev.target as HTMLInputElement

        if (!target || value === undefined || !this.formData.regressors) {
            return
        }

        // Auto-select first attribute when asset changes
        if (target.name === 'asset_id') {
            this.formData.regressors[index].attribute_name =
                this.attributeSelectList
                    .get(value as string)
                    ?.values()
                    .next().value ?? ''
        }

        this.formData.regressors[index] = {
            ...this.formData.regressors[index],
            [target.name]: value
        }
        this.requestUpdate()
    }

    // Update lifecycle
    updated(_changedProperties: PropertyValues): void {
        void _changedProperties // Explicitly acknowledge unused parameter
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
            // Create a deep copy of the model config for the form data
            this.formData = JSON.parse(JSON.stringify(this.modelConfig))
            this.loading = false
            return
        } catch (err) {
            this.loading = false
            console.error(err)
        }
    }

    // Handle the Vaadin Router location change event
    onAfterEnter(location: RouterLocation) {
        this.configId = location.params.id as string
        return this.setupEditor()
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
        // check target properties
        if (!this.formData.target.asset_id || !this.formData.target.attribute_name) {
            return false
        }

        // check all regressors
        if (this.formData.regressors) {
            for (const regressor of this.formData.regressors) {
                if (!regressor.asset_id || !regressor.attribute_name) {
                    return false
                }
            }
        }

        // Check other inputs
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
        this.formData.regressors = this.formData.regressors ?? []

        this.formData.regressors.push({
            asset_id: '',
            attribute_name: '',
            cutoff_timestamp: new Date().getTime()
        })
        this.requestUpdate()
    }

    // Handle deleting a regressor
    handleDeleteRegressor(index: number) {
        this.formData.regressors.splice(index, 1)

        // Clean up regressors if all are deleted
        if (this.formData.regressors?.length === 0) {
            this.formData.regressors = null
        }

        this.requestUpdate()
    }

    // Get the regressor template
    getRegressorTemplate(index: number) {
        const regressor = this.formData.regressors[index]
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
                            .options="${[...this.assetSelectList.entries()].slice(0, this.assetSearchSize)}"
                            .searchProvider="${this.assetSelectList.size > 0 ? this.searchAssets.bind(this) : null}"
                        ></or-mwc-input>

                        <or-mwc-input
                            type="${InputType.SELECT}"
                            name="attribute_name"
                            @or-mwc-input-changed="${(e: OrInputChangedEvent) => this.handleRegressorInput(e, index)}"
                            label="Attribute"
                            .value="${regressor.attribute_name}"
                            .options="${[...(this.attributeSelectList.get(regressor.asset_id) ?? new Map())]}"
                        ></or-mwc-input>

                        <or-mwc-input
                            type="${InputType.DATETIME}"
                            name="cutoff_timestamp"
                            @or-mwc-input-changed="${(e: OrInputChangedEvent) => this.handleRegressorInput(e, index)}"
                            label="Use datapoints since"
                            .value="${regressor.cutoff_timestamp}"
                            required
                        ></or-mwc-input>

                        <or-mwc-input
                            type="${InputType.BUTTON}"
                            icon="delete"
                            @click="${() => this.handleDeleteRegressor(index)}"
                        ></or-mwc-input>
                    </div>
                </div>
            </or-panel>
        `
    }

    // Get the add regressor template
    getAddRegressorTemplate() {
        return html`
            <or-panel>
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
        `
    }

    // Search provider for the asset select list
    protected async searchAssets(search?: string): Promise<[any, string][]> {
        const options = [...this.assetSelectList.entries()]
        if (!search) {
            return options.slice(0, this.assetSearchSize)
        }
        const searchTerm = search.toLowerCase()
        return options.filter(([, label]) => label.toLowerCase().includes(searchTerm)).slice(0, this.assetSearchSize)
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
                        <div class="row">
                            <or-mwc-input
                                type="${InputType.SELECT}"
                                name="target.asset_id"
                                @or-mwc-input-changed="${this.handleTargetInput}"
                                label="Asset"
                                .value="${this.formData.target.asset_id}"
                                .options="${[...this.assetSelectList.entries()].slice(0, this.assetSearchSize)}"
                                .searchProvider="${this.assetSelectList.size > 0 ? this.searchAssets.bind(this) : null}"
                            ></or-mwc-input>

                            <or-mwc-input
                                type="${InputType.SELECT}"
                                name="target.attribute_name"
                                @or-mwc-input-changed="${this.handleTargetInput}"
                                label="Attribute"
                                .value="${this.formData.target.attribute_name}"
                                .options="${[...(this.attributeSelectList.get(this.formData.target.asset_id) ?? new Map())]}"
                            ></or-mwc-input>

                            <or-mwc-input
                                type="${InputType.DATETIME}"
                                name="target.cutoff_timestamp"
                                @or-mwc-input-changed="${this.handleTargetInput}"
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
                ${this.formData.regressors ? this.formData.regressors.map((_regressor, index) => this.getRegressorTemplate(index)) : html``}
                ${this.getAddRegressorTemplate()}
            </form>
        `
    }
}
