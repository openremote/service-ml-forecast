import { css, html, LitElement } from "lit";
import { state, customElement, property } from "lit/decorators.js";
import { ProphetModelConfig, ProphetSeasonalityModeEnum } from "../services/models";
import { ApiService } from "../services/api-service";
import { RouterLocation } from "@vaadin/router";
import "@openremote/or-icon";
import "@openremote/or-panel";
import * as Core from "@openremote/core";
import { unsafeCSS } from "lit";
import { InputType, OrInputChangedEvent } from "@openremote/or-mwc-components/or-mwc-input";



enum TimeDurationUnit {
    MINUTE = "M",
    HOUR = "H",
}

enum PandasTimeUnit {
    MINUTE = "min",
    HOUR = "h",
}

@customElement("page-config-viewer")
export class PageConfigViewer extends LitElement {


    static get styles() {
        return css`
            :host {
                --or-panel-background-color: #fff;
                --or-panel-heading-text-transform: uppercase;
                --or-panel-heading-color: var(--or-app-color3, ${unsafeCSS(Core.DefaultColor3)});
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

            or-mwc-input[type="switch"] {
                flex: none;
             
            }

            #config-name {
                min-width: 400px;
            }

            #config-header {
                width: 100%;
                display: flex;
                flex-direction: row;
                align-items: center;
                justify-content: space-between;
            }
        `;
    }

    @property({ type: String })
    configId?: string;

    @property({ type: Object })
    private modelConfig: ProphetModelConfig | null = null;

    @property({ type: Object })
    private formData: ProphetModelConfig = new ProphetModelConfig();


    // Extract the number from the ISO 8601 Duration string
    getNumberFromDuration(duration: string): number | null {
        const match = (/PT(\d+)([HM])/).exec(duration);
        return match ? parseInt(match[1], 10) : null;
    }

    // Extract the unit from the ISO 8601 Duration string
    getUnitFromDuration(duration: string): string | null {
        const match = (/PT(\d+)([HM])/).exec(duration);
        return match ? match[2] : null;
    }
    
    // Extract the number from the Pandas Offset string
    getNumberFromPandasOffset(offset: string): number | null {
        const match = (/(\d+)(min|h)/).exec(offset);
        return match ? parseInt(match[1], 10) : null;
    }

    // Extract the unit from the Pandas Offset string
    getUnitFromPandasOffset(offset: string): string | null {
        const match = (/(\d+)(min|h)/).exec(offset);
        return match ? match[2] : null;
    }


    @property({ type: Boolean })
    private loading: boolean = true;

    private readonly apiService: ApiService = new ApiService();

    onAfterEnter(location: RouterLocation) {
        this.configId = location.params.id as string;
        return this.loadConfig();
    }

   
    private async loadConfig() {
        if (!this.configId) {
            this.loading = false;
            return;
        }

        try {
            this.modelConfig = await this.apiService.getModelConfig(this.configId);
            this.loading = false;
            this.formData = this.modelConfig;
            console.log(this.formData);
        } catch (err) {
            this.loading = false;
        }
    }

    onInput(ev: OrInputChangedEvent) {
        let value = ev.detail?.value;
        const target = ev.target as HTMLInputElement;

        if (!target) {
            return;
        }
        if (value === undefined) {
            return;
        }
        const name = target.name;

        // handle checkboxes
        if (name === "daily_seasonality" || name === "weekly_seasonality" || name === "yearly_seasonality") {
            value = (target as HTMLInputElement).checked;
            return;
        }

        console.log(name, value);
        this.formData = {
            ...this.formData,
            [name]: value
        };

        

    }

    protected render() {
        if (this.loading) {
            return html`<div>Loading config details...</div>`;
        }

        if (!this.modelConfig?.id) {
            return html`<div>Creating new config</div>`;
        }

        return html`
            <form id="config-form" class="config-viewer">
                <div id="config-header">
                    <or-mwc-input name="name" outlined type="${InputType.TEXT}" label="Model Name" @or-mwc-input-changed="${this.onInput}"
                                  value="${this.formData.name}" required minlength="1" maxlength="255"
                    ></or-mwc-input>
                    <div id="config-header-controls">
                        <or-mwc-input type="${InputType.BUTTON}" id="save-btn" label="save" raised"></or-mwc-input>
                    </div>
                </div>

                <!-- Model selection -->
                <or-panel heading="MODEL">
                    <div class="column">
                        <div class="row">
                            <or-mwc-input class="header-item" name="type" required @or-mwc-input-changed="${this.onInput}"
                            label="Model Type" type="${InputType.SELECT}" .options="${[["prophet", "Prophet"]]}" value="${this.formData.type}">
                        </or-mwc-input>
                        </div>
                    </div>
                </or-panel>

                <!-- Forecast generation, e.g. the schedule -->
                <or-panel heading="FORECAST GENERATION">
                    <div class="column">
                        <div class="row">
                            <or-mwc-input type="${InputType.TEXT}" name="forecast_interval" @or-mwc-input-changed="${this.onInput}"
                                label="Generate new forecast every" value="${this.formData.forecast_interval}" required></or-mwc-input>
                        </div>
         
                        <div class="row">
                            <!-- forecast_periods -->
                            <or-mwc-input type="${InputType.NUMBER}" name="forecast_periods" @or-mwc-input-changed="${this.onInput}"
                                    label="Forecasted datapoints" value="${this.formData.forecast_periods}" required></or-mwc-input>
                            <or-mwc-input type="${InputType.TEXT}" name="forecast_frequency" @or-mwc-input-changed="${this.onInput}"
                                label="Time between datapoints" value="${this.formData.forecast_frequency}" required></or-mwc-input>
                        </div>
                    </div>
                </or-panel>

                <!-- Forecast target, the asset and attribute to forecast -->
                <or-panel heading="FORECAST TARGET">
                </or-panel>

                <!-- Model training, e.g the schedule-->
                <or-panel heading="MODEL TRAINING">
                    <div class="column">
                        <div class="row">
                            <or-mwc-input type="${InputType.TEXT}" name="training_interval" @or-mwc-input-changed="${this.onInput}"
                                label="Training interval" value="${this.formData.training_interval}" required></or-mwc-input>
                        </div>
                    </div>
                </or-panel>

                <!-- Model parameters, these will be dynamic based on the model type -->
                <or-panel heading="PARAMETERS">
                    <div class="column">
                        <div class="row">
                            <!-- changepoint_range -->
                            <or-mwc-input type="${InputType.NUMBER}" name="changepoint_range" @or-mwc-input-changed="${this.onInput}"
                                label="Changepoint range" value="${this.formData.changepoint_range}" max="1.0" min="0.0" step="0.01" required></or-mwc-input>
                            <!-- changepoint_prior_scale -->
                            <or-mwc-input type="${InputType.NUMBER}" name="changepoint_prior_scale" @or-mwc-input-changed="${this.onInput}"
                                label="Changepoint prior scale" value="${this.formData.changepoint_prior_scale}" max="1.0" min="0.0" step="0.01" required></or-mwc-input>
                        </div>
                        <div class="row">
                            <!-- seasonality_mode -->
                            <or-mwc-input type="${InputType.SELECT}" .options="${[[ProphetSeasonalityModeEnum.ADDITIVE, "Additive"], [ProphetSeasonalityModeEnum.MULTIPLICATIVE, "Multiplicative"]]}" name="seasonality_mode" @or-mwc-input-changed="${this.onInput}"
                                label="Seasonality mode" value="${this.formData.seasonality_mode}" required></or-mwc-input>
                            <!-- daily_seasonality -->
                            <or-mwc-input type="${InputType.SWITCH}" name="daily_seasonality" @or-mwc-input-changed="${this.onInput}"
                                label="Daily seasonality" value="${this.formData.daily_seasonality}" required></or-mwc-input>
                            <!-- weekly_seasonality -->
                            <or-mwc-input type="${InputType.SWITCH}" name="weekly_seasonality" @or-mwc-input-changed="${this.onInput}"
                                label="Weekly seasonality" value="${this.formData.weekly_seasonality}" required></or-mwc-input>
                            <!-- yearly_seasonality -->
                            <or-mwc-input  type="${InputType.SWITCH}"  name="yearly_seasonality" @or-mwc-input-changed="${this.onInput}"
                                    label="Yearly seasonality" value="${this.formData.yearly_seasonality}" required></or-mwc-input>
                        </div>
                    </div>
                </or-panel>

                <!-- Regressors, these will be dynamic based on the model type -->
                <or-panel heading="REGRESSOR">
                </or-panel>
            </form>
                
        `;
    }
}