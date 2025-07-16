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

import { OrMwcTable, TableColumn, TableConfig, TableRow } from '@openremote/or-mwc-components/or-mwc-table';
import { css, html, TemplateResult } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { ModelConfig } from '../services/models';
import { getRootPath } from '../common/util';
import { Router } from '@vaadin/router';
import { InputType } from '@openremote/or-mwc-components/or-mwc-input';
import * as Model from '@openremote/model';

@customElement('configs-table')
export class ConfigsTable extends OrMwcTable {
    static get styles() {
        return [
            super.styles,
            css`
                .mdc-data-table__row:not(.mdc-data-table__row--selected):hover {
                    background-color: transparent !important;
                }

                .table-container {
                    min-height: 300px;
                    padding-bottom: 10px;
                }

                .no-data-section {
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    min-height: 150px;
                    flex-direction: column;
                    gap: 10px;
                }

                td:has(> .actions-container) {
                    min-width: 250px;
                }

                .state-label {
                    font-size: 12px;
                    font-weight: 500;
                    padding: 8px 12px;
                    border-radius: 30px;
                    font-weight: 600;
                }

                td:has(> .state-label) {
                    width: 110px;
                }

                .state-label.enabled {
                    border: 1px solid var(--or-app-color3);
                    color: var(--or-app-color3);
                }

                .state-label.disabled {
                    border: 1px solid var(--or-app-color3);
                    color: var(--or-app-color3);
                    opacity: 0.5;
                }

                .warning {
                    color: var(--or-app-color6);
                    display: flex;
                    align-items: center;
                    gap: 5px;
                }
            `
        ] as any; // Cast to bypass strict type check by OrMwcTable extension
    }

    @property({ type: Array })
    public modelConfigs: ModelConfig[] = [];

    @property({ type: Array })
    public configAssets: Model.Asset[] = [];

    @property({ type: String })
    public realm: string = '';

    public columns: TableColumn[] = [
        { title: 'State', isSortable: true },
        { title: 'Name', isSortable: true },
        { title: 'Type', isSortable: true, hideMobile: true },
        { title: 'Asset', isSortable: true },
        { title: 'Attribute', isSortable: true },
        { title: 'Actions', isSortable: false }
    ];

    protected readonly rootPath = getRootPath();

    protected config: TableConfig = {
        fullHeight: true,
        stickyFirstColumn: false,
        pagination: {
            enable: true,
            options: [10]
        }
    };

    protected sortIndex = 0;
    protected sortDirection: 'ASC' | 'DESC' = 'DESC';

    // Construct the state row template
    protected getStateRowTemplate(config: ModelConfig): TemplateResult {
        return html` <span class="state-label ${config.enabled ? 'enabled' : 'disabled'}">
            ${config.enabled ? 'Enabled' : 'Disabled'}
        </span>`;
    }

    // Construct the actions row template
    protected getActionsRowTemplate(config: ModelConfig): TemplateResult {
        const handleEdit = (e: Event) => {
            e.stopPropagation();
            this.dispatchEvent(
                new CustomEvent('edit-config', {
                    detail: config,
                    bubbles: true,
                    composed: true
                })
            );
        };

        const handleDelete = (e: Event) => {
            e.stopPropagation();
            this.dispatchEvent(
                new CustomEvent('delete-config', {
                    detail: config,
                    bubbles: true,
                    composed: true
                })
            );
        };

        return html`
            <div class="actions-container">
                <or-mwc-input type="${InputType.BUTTON}" outlined icon="pencil" label="Edit" @click="${handleEdit}"></or-mwc-input>
                <or-mwc-input
                    type="${InputType.BUTTON}"
                    outlined
                    icon="delete"
                    style="margin-left: 10px;"
                    label="Delete"
                    @click="${handleDelete}"
                ></or-mwc-input>
            </div>
        `;
    }

    // Construct the asset name template
    protected getAssetNameTemplate(assetId: string): TemplateResult {
        const asset = this.configAssets.find((a) => a.id === assetId);

        if (!asset) {
            return html`<span title="Asset ID: ${assetId} could not be found" class="warning"
                ><or-icon icon="alert-box-outline"></or-icon> Not found</span
            >`;
        }

        return html`<span title="Asset ID: ${assetId}">${asset.name}</span>`;
    }

    // Construct the table rows
    protected getTableRows(configs: ModelConfig[]): TableRow[] {
        return configs.map((config) => ({
            content: [
                this.getStateRowTemplate(config) as any,
                config.name,
                config.type.charAt(0).toUpperCase() + config.type.slice(1), // Capitalize first letter
                this.getAssetNameTemplate(config.target.asset_id),
                config.target.attribute_name,
                this.getActionsRowTemplate(config)
            ]
        }));
    }

    // Construct the no data section template
    protected getNoDataSectionTemplate(): TemplateResult {
        if (this.modelConfigs.length === 0) {
            return html` <div class="no-data-section">
                <div>No forecast configurations found.</div>
                <or-mwc-input
                    type="${InputType.BUTTON}"
                    outlined
                    icon="plus"
                    label="Configure new forecast"
                    @click="${this.handleAddConfig}"
                ></or-mwc-input>
            </div>`;
        }

        return html``;
    }

    // Handle the add config click
    protected handleAddConfig() {
        Router.go(`${this.rootPath}/${this.realm}/configs/new`);
    }

    // Render the table
    protected render() {
        return html`<div class="table-container">${super.render()} ${this.getNoDataSectionTemplate()}</div>`;
    }

    // Update the table rows when the model configs change
    protected willUpdate(changedProperties: Map<string, any>): void {
        super.willUpdate(changedProperties);
        if (changedProperties.has('modelConfigs')) {
            this.rows = this.getTableRows(this.modelConfigs);
        }
    }
}
