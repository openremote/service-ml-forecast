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
import { customElement, state } from 'lit/decorators.js';
import { BasicAsset, ModelConfig } from '../services/models';
import { Router } from '@vaadin/router';
import { getRootPath } from '../common/util';
import { InputType } from '@openremote/or-mwc-components/or-mwc-input';
import { showOkCancelDialog } from '@openremote/or-mwc-components/or-mwc-dialog';
import { showSnackbar } from '@openremote/or-mwc-components/or-mwc-snackbar';
import { APIService } from '../services/api-service';
import { consume } from '@lit/context';
import { realmContext } from './app-layout';
import { when } from 'lit/directives/when.js';
@customElement('page-config-list')
export class PageConfigList extends LitElement {
    @consume({ context: realmContext })
    realm = '';

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
                --or-icon-fill: var(--or-app-color3);
            }
            .title {
                font-size: 18px;
                font-weight: bold;
                display: flex;
                flex-direction: row;
                align-items: center;
                color: var(--or-app-color3);
            }
        `;
    }

    protected readonly rootPath = getRootPath();

    @state()
    protected modelConfigs?: ModelConfig[] = [];

    @state()
    protected configAssets?: BasicAsset[] = [];

    @state()
    protected loading: boolean = true;

    @state()
    protected error: string | null = null;

    // Lifecycle, when component is connected to the DOM
    connectedCallback() {
        super.connectedCallback();
        this.loadModelConfigs();
    }

    // Load the model configs from the API
    async loadModelConfigs() {
        try {
            this.modelConfigs = await APIService.getModelConfigs(this.realm);
            this.configAssets = await APIService.getOpenRemoteAssetsById(
                this.realm,
                this.modelConfigs.map((c) => c.target.asset_id)
            );
            this.loading = false;
        } catch (error) {
            console.error('Failed to fetch model configs:', error);
            this.error = `Failed to retrieve forecast configurations`;
            this.modelConfigs = [];
            this.configAssets = [];
            this.loading = false;
        }
    }

    // Handle the `edit-config` event
    protected handleEditConfig(e: CustomEvent<ModelConfig>) {
        const config = e.detail;
        Router.go(`${this.rootPath}/${this.realm}/configs/${config.id}`);
    }

    // Handle the `delete-config` event
    protected async handleDeleteConfig(e: CustomEvent<ModelConfig>) {
        const config = e.detail;
        if (!config.id) {
            console.error('Config ID is required');
            return;
        }

        // Show a confirmation dialog
        const result = await showOkCancelDialog('Delete config', `Are you sure you want to delete the config: ${config.name}?`, 'Delete');

        if (result) {
            try {
                await APIService.deleteModelConfig(this.realm, config.id);
                this.modelConfigs = this.modelConfigs?.filter((c) => c.id !== config.id);
            } catch (error) {
                showSnackbar(undefined, `Failed to delete config: ${error}`);
                console.error('Failed to delete config:', error);
            }
        }
    }

    // Handle the `add-config` event
    protected handleAddConfig() {
        Router.go(`${this.rootPath}/${this.realm}/configs/new`);
    }

    // Construct the configs table template
    protected getConfigsTableTemplate() {
        if (this.loading) {
            return html`<loading-spinner></loading-spinner>`;
        }

        return html`<configs-table
            @edit-config="${this.handleEditConfig}"
            @delete-config="${this.handleDeleteConfig}"
            .modelConfigs="${this.modelConfigs}"
            .configAssets="${this.configAssets}"
            .realm="${this.realm}"
        ></configs-table>`;
    }

    // Render the page
    protected render() {
        return html`
            <or-panel heading="">
                <div class="config-header">
                    <div class="title-container">
                        <or-icon icon="chart-bell-curve"></or-icon>
                        <span class="title">Forecast Configurations</span>
                    </div>

                    <or-mwc-input
                        type="${InputType.BUTTON}"
                        icon="plus"
                        label="configure new forecast"
                        @click="${this.handleAddConfig}"
                    ></or-mwc-input>
                </div>

                ${when(
                    this.error,
                    () => html`<alert-message .alert="${this.error}"></alert-message>`,
                    () => this.getConfigsTableTemplate()
                )}
            </or-panel>
        `;
    }
}
