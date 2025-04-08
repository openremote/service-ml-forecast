import { html, LitElement } from "lit";
import { state, customElement } from "lit/decorators.js";
import { ModelConfig } from "../api/models";
import { ServiceClient } from "../api/service-client";
import { RouterLocation } from "@vaadin/router";


@customElement("page-config-details")
export class PageConfigDetails extends LitElement {

    @state()
    configId?: string;

    @state()
    private modelConfig: ModelConfig | null = null;

    @state()
    private loading: boolean = true;

    private readonly serviceClient: ServiceClient = new ServiceClient();


    onBeforeEnter(location: RouterLocation) {
        this.configId = location.params.id as string;
        return this.loadConfig();
    }


    private async loadConfig() {
        if (!this.configId) {
            this.loading = false;
            return;
        }

        try {
            this.modelConfig = await this.serviceClient.getModelConfig(this.configId);
            this.loading = false;
        } catch (err) {
            this.loading = false;
        }
    }

    protected render() {
        if (this.loading) {
            return html`<div>Loading config details...</div>`;
        }

        if (!this.modelConfig) {
            return html`<div>Config not found</div>`;
        }

        return html`
            <div>
                <h1>Model Config: ${this.modelConfig.name}</h1>
                
                <div>
                    <h2>Basic Information</h2>
                    <p><strong>ID:</strong> ${this.modelConfig.id}</p>
                    <p><strong>Realm:</strong> ${this.modelConfig.realm}</p>
                    <p><strong>Enabled:</strong> ${this.modelConfig.enabled ? 'Yes' : 'No'}</p>
                    <p><strong>Type:</strong> ${this.modelConfig.type}</p>
                </div>
                
                <div>
                    <h2>Target</h2>
                    <p><strong>Asset ID:</strong> ${this.modelConfig.target.asset_id}</p>
                    <p><strong>Attribute:</strong> ${this.modelConfig.target.attribute_name}</p>
                    <p><strong>Cutoff Timestamp:</strong> ${new Date(this.modelConfig.target.cutoff_timestamp).toLocaleString()}</p>
                </div>
                
                <div>
                    <h2>Forecast Settings</h2>
                    <p><strong>Forecast Interval:</strong> ${this.modelConfig.forecast_interval}</p>
                    <p><strong>Training Interval:</strong> ${this.modelConfig.training_interval}</p>
                    <p><strong>Forecast Periods:</strong> ${this.modelConfig.forecast_periods}</p>
                    <p><strong>Forecast Frequency:</strong> ${this.modelConfig.forecast_frequency}</p>
                </div>
                
  
            </div>
        `;
    }
}