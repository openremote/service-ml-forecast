import { css, html, LitElement } from "lit";
import { state, customElement, property } from "lit/decorators.js";
import { ModelConfig } from "../services/models";
import { ApiService } from "../services/api-service";
import { RouterLocation } from "@vaadin/router";
import "@openremote/or-icon";
import "@openremote/or-panel";
import * as Core from "@openremote/core";
import { unsafeCSS } from "lit";
import { InputType } from "@openremote/or-mwc-components/or-mwc-input";

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
                width: 20%;
                max-width: 300px;
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

    @state()
    configId?: string;

    @property({ type: Object })
    private modelConfig: ModelConfig | null = null;

    @property({ type: Boolean })
    private loading: boolean = true;

    private readonly apiService: ApiService = new ApiService();

    onAfterEnter(location: RouterLocation) {
        this.configId = location.params.id as string;
        return this.loadConfig();
    }



    DurationTimeUnits = [["M", "Minutes"], ["H", "Hours"]];
    PandasTimeUnits = [["min", "Minutes"], ["h", "Hours"]];

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

    
    private async loadConfig() {
        if (!this.configId) {
            this.loading = false;
            return;
        }

        try {
            this.modelConfig = await this.apiService.getModelConfig(this.configId);
            this.loading = false;
        } catch (err) {
            this.loading = false;
        }
    }


    protected render() {
        if (this.loading) {
            return html`<div>Loading config details...</div>`;
        }

        if (!this.modelConfig?.id) {
            return html`<div>Creating new config</div>`;
        }

        return html`
            <div class="config-viewer">
                <div id="config-header">
                    <or-mwc-input id="config-name" outlined type="${InputType.TEXT}" label="Model Name" focused
                                  value="${this.modelConfig.name}" required minlength="1" maxlength="255"
                    ></or-mwc-input>
                    <div id="config-header-controls">
                        <or-mwc-input type="${InputType.BUTTON}" id="save-btn" label="save" raised></or-mwc-input>
                    </div>
                </div>

                <!-- Model selection -->
                <or-panel heading="MODEL">
                    <div class="column">
                        <div class="row">
                            <or-mwc-input class="header-item" id="model-type-input" focused required 
                            label="Model Type" type="${InputType.SELECT}" .options="${[["prophet", "Prophet"]]}" value="${this.modelConfig.type}">
                        </or-mwc-input>
                        </div>
                    </div>
                </or-panel>

                <!-- Forecast generation, e.g. the schedule -->
                <or-panel heading="FORECAST GENERATION">
                    <div class="column">
               
                        <div class="row">
                            <!-- forecast_interval (split into number and unit) -->
                            <or-mwc-input type="${InputType.NUMBER}" id="forecast-interval" 
                                label="Generate new forecast every" value="${this.getNumberFromDuration(this.modelConfig.forecast_interval)}" required></or-mwc-input>
                            <!-- forecast_interval (UNIT) -->
                            <or-mwc-input type="${InputType.SELECT}" id="forecast-interval-unit" .options="${this.DurationTimeUnits}" 
                                label="Unit" value="${this.getUnitFromDuration(this.modelConfig.forecast_interval)}" required></or-mwc-input>
                        </div>
         
                        <div class="row">
                            <!-- forecast_periods -->
                            <or-mwc-input type="${InputType.NUMBER}" id="forecast-periods" 
                                    label="Forecasted datapoints" value="${this.modelConfig.forecast_periods}" required></or-mwc-input>
                            <!-- forecast_frequency (split into number and unit) -->
                            <or-mwc-input type="${InputType.NUMBER}" id="forecast-frequency" 
                                label="Time between datapoints" value="${this.getNumberFromPandasOffset(this.modelConfig.forecast_frequency)}" required></or-mwc-input>
                            <!-- forecast_frequency (UNIT) -->
                            <or-mwc-input type="${InputType.SELECT}" id="forecast-frequency-unit" .options="${this.PandasTimeUnits}" 
                                label="Unit" value="${this.getUnitFromPandasOffset(this.modelConfig.forecast_frequency)}" required></or-mwc-input>
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
                            <or-mwc-input type="${InputType.NUMBER}" id="training-interval" 
                                label="Training interval" value="${this.getNumberFromDuration(this.modelConfig.training_interval)}" required></or-mwc-input>
                            <!-- training_interval (UNIT) -->
                            <or-mwc-input type="${InputType.SELECT}" id="training-interval-unit" .options="${this.DurationTimeUnits}" 
                                label="Unit" value="${this.getUnitFromDuration(this.modelConfig.training_interval)}" required></or-mwc-input>
                        </div>
                    </div>
                </or-panel>

                <!-- Model parameters, these will be dynamic based on the model type -->
                <or-panel heading="PARAMETERS">
                    <div class="column">
                        <div class="row">
                            <!-- changepoint_range -->
                            <or-mwc-input type="${InputType.NUMBER}" id="changepoint-range" 
                                label="Changepoint range" value="${this.modelConfig.changepoint_range}" max="1.0" min="0.0" step="0.01" required></or-mwc-input>
                            <!-- changepoint_prior_scale -->
                            <or-mwc-input type="${InputType.NUMBER}" id="changepoint-prior-scale" 
                                label="Changepoint prior scale" value="${this.modelConfig.changepoint_prior_scale}" max="1.0" min="0.0" step="0.01" required></or-mwc-input>
                            <!-- daily_seasonality -->
                            <or-mwc-input type="${InputType.CHECKBOX}" id="daily-seasonality" 
                                label="Daily seasonality" value="${this.modelConfig.daily_seasonality}" required></or-mwc-input>
                            <!-- weekly_seasonality -->
                            <or-mwc-input type="${InputType.CHECKBOX}" id="weekly-seasonality" 
                                label="Weekly seasonality" value="${this.modelConfig.weekly_seasonality}" required></or-mwc-input>
                            <!-- yearly_seasonality -->
                            <or-mwc-input type="${InputType.CHECKBOX}" id="yearly-seasonality" 
                                    label="Yearly seasonality" value="${this.modelConfig.yearly_seasonality}" required></or-mwc-input>
                        </div>
                    </div>
                </or-panel>

                <!-- Regressors, these will be dynamic based on the model type -->
                <or-panel heading="REGRESSOR">
                </or-panel>
            </div>
                
        `;
    }
}