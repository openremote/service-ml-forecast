import {html, LitElement} from "lit";
import {state, customElement} from "lit/decorators.js";
import { ModelConfig } from "../api/models";
import { ServiceClient } from "../api/service-client";
import "@openremote/or-mwc-components/or-mwc-input";


@customElement("page-config-list")
export class PageConfigList extends LitElement {

    @state()
    private modelConfigs: ModelConfig[] = [];

    private readonly serviceClient: ServiceClient = new ServiceClient();

    connectedCallback() {
        super.connectedCallback();
        this.serviceClient.getModelConfigs().then(configs => {
            this.modelConfigs = configs;
        });
    }

    protected render() {
        return html`
            <h1>Model Configs</h1>
            <or-mwc-input type="button" label="Search"></or-mwc-input>
            <ul>
                ${this.modelConfigs.map(config => html`<li><a href="/configs/${config.id}">${config.name}</a></li>`)}
            </ul>
        `;  
    }
}