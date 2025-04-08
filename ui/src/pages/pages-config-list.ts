import {html, LitElement, css} from "lit";
import {customElement} from "lit/decorators.js";
import { ModelConfig } from "../api/models";
import { Router } from '@vaadin/router';
import "../components/configs-table";


@customElement("page-config-list")
export class PageConfigList extends LitElement {


    private _handleEditConfig(e: CustomEvent<ModelConfig>) {
        const config = e.detail;
        Router.go(`/configs/${config.id}`);
    }

    private _handleDeleteConfig(e: CustomEvent<ModelConfig>) {
        const config = e.detail;
        console.log("Delete config:", config);
        alert(`Delete requested for config: ${config.name}`);
    }

    protected render() {
        return html`
            <h1>Forecast Configs</h1>
            <configs-table
                @edit-config="${this._handleEditConfig}"
                @delete-config="${this._handleDeleteConfig}"
            >
            </configs-table>
        `;
    }
}