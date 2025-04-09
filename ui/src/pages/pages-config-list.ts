import { html, LitElement, css } from "lit";
import { customElement, property } from "lit/decorators.js";
import { ModelConfig } from "../services/models";
import { Router } from '@vaadin/router';
import "../components/configs-table";
import * as Core from "@openremote/core";
import { unsafeCSS } from "lit";
import "@openremote/or-panel";
import { getRealm } from "../util";
import { ApiService } from "../services/api-service";
import "../components/loading-spinner";
import { InputType } from "@openremote/or-mwc-components/or-mwc-input";
import {showOkCancelDialog} from "@openremote/or-mwc-components/or-mwc-dialog";


@customElement("page-config-list")
export class PageConfigList extends LitElement {


    static get styles() {
        return css`

            :host {
                display: block;
                --or-panel-background-color: #fff;
            }

            .config-header {
                display: flex;
                flex-direction: row;
                align-items: center;
                justify-content: space-between;
                height: 65px;
            }

            .title-container {
                display: flex;
                flex-direction: row;
                align-items: center;
                gap: 4px;
                --or-icon-fill: var(--or-app-color3, ${unsafeCSS(Core.DefaultColor4)});
            }
            .title {
                font-size: 18px;
                font-weight: bold;
                display: flex;
                flex-direction: row;
                align-items: center;
                color: var(--or-app-color3, ${unsafeCSS(Core.DefaultColor3)});
            }
        `;
    }


    private readonly apiService: ApiService = new ApiService();

    @property({ type: Array })
    private modelConfigs?: ModelConfig[] = [];

    @property({ type: Boolean })
    private loading: boolean = true;

    connectedCallback() {
        super.connectedCallback();
        this.loadModelConfigs();
    }

    async loadModelConfigs() {
        try {
            this.modelConfigs = await this.apiService.getModelConfigs();
            this.loading = false;
        } catch (error) {
            console.error("PageConfigList: Failed to fetch model configs:", error);
            this.modelConfigs = []; 
            this.loading = false;
        }
    }


    private handleEditConfig(e: CustomEvent<ModelConfig>) {
        const config = e.detail;
        const realm = getRealm(window.location.pathname);
        Router.go(`/${realm}/configs/${config.id}`);
    }

    private async handleDeleteConfig(e: CustomEvent<ModelConfig>) {
        const config = e.detail;
        if (!config.id) {
            console.error("Config ID is required");
            return;
        }


        const result = await showOkCancelDialog("Delete config", `Are you sure you want to delete the config: ${config.name}?`, "Delete")

        if (result) {


        try {
            await this.apiService.deleteModelConfig(config.id);
            this.modelConfigs = this.modelConfigs?.filter(c => c.id !== config.id);
        } catch (error) {
                console.error("Failed to delete config:", error);
            }
        }
    }

    private handleAddConfig() {
        const realm = getRealm(window.location.pathname);
        Router.go(`/${realm}/configs/new`);
    }

    private getConfigsTableTemplate() {

        if (this.loading) {
            return html`<loading-spinner></loading-spinner>`;
        }

        return html`<configs-table
            @edit-config="${this.handleEditConfig}"
            @delete-config="${this.handleDeleteConfig}"
            .modelConfigs="${this.modelConfigs}"
        >`;
    }

    protected render() {
        return html`
            <or-panel heading="">
                <div class="config-header">
                    <div class="title-container">
                        <or-icon icon="chart-bell-curve"></or-icon>
                    <span class="title">Forecast Configurations - (DEBUG: ${getRealm(window.location.pathname)})</span>
                </div>
                <or-mwc-input type="${InputType.BUTTON}" icon="plus" label="configure new forecast" @click="${this.handleAddConfig}"></or-mwc-input>
            </div>
            ${this.getConfigsTableTemplate()}
            </configs-table>
            </or-panel>
        `;
    }
}