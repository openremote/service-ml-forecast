import {html, LitElement, css} from "lit";
import {customElement} from "lit/decorators.js";
import { ModelConfig } from "../api/models";
import { Router } from '@vaadin/router';
import "../components/configs-table";
import { DefaultColor3, DefaultColor4 } from "@openremote/core";
import { unsafeCSS } from "lit";
import "@openremote/or-panel";

@customElement("page-config-list")
export class PageConfigList extends LitElement {


    static get styles() {
        return css`

            .config-header {
                display: flex;
                flex-direction: row;
                align-items: center;
                justify-content: space-between;
                height: 50px;
            }

            .title-container {
                display: flex;
                flex-direction: row;
                align-items: center;
                gap: 4px;
                --or-icon-fill: var(--or-app-color3, ${unsafeCSS(DefaultColor4)});
            }
            .title {
                font-size: 18px;
                font-weight: bold;
                display: flex;
                flex-direction: row;
                align-items: center;
                color: var(--or-app-color3, ${unsafeCSS(DefaultColor3)}
            

            }
        `;
    }


    private handleEditConfig(e: CustomEvent<ModelConfig>) {
        const config = e.detail;
        Router.go(`/configs/${config.id}`);
    }

    private handleDeleteConfig(e: CustomEvent<ModelConfig>) {
        const config = e.detail;
        console.log("Delete config:", config);
        alert(`Delete requested for config: ${config.name}`);
    }

    private handleAddConfig() {
        Router.go(`/configs/new`);
    }

    protected render() {
        return html`
            <or-panel heading="">
                <div class="config-header">
                    <div class="title-container">
                        <or-icon icon="chart-bell-curve"></or-icon>
                    <span class="title">Forecast Configurations</span>
                </div>
                <or-mwc-input type="button" outlined icon="plus" label="Add Config" @click="${this.handleAddConfig}"></or-mwc-input>
            </div>
            <configs-table
                @edit-config="${this.handleEditConfig}"
                @delete-config="${this.handleDeleteConfig}"
            >
            </configs-table>
            </or-panel>
        `;
    }
}