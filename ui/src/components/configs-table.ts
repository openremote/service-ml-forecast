import { OrMwcTable, TableColumn, TableRow, TableConfig } from "@openremote/or-mwc-components/or-mwc-table";
import { css, html, TemplateResult } from "lit";
import { customElement, property } from "lit/decorators.js";
import { ModelConfig } from "../services/models";
import "@openremote/or-mwc-components/or-mwc-input";
import { getRealm } from "../util";
import { Router } from "@vaadin/router";
import * as Colors from "@openremote/core";
import { unsafeCSS } from "lit";
import { InputType } from "@openremote/or-mwc-components/or-mwc-input";


@customElement("configs-table")
export class ConfigsTable extends OrMwcTable {

    static get styles() {
        return [
            super.styles,
            css`
                .mdc-data-table__row:not(.mdc-data-table__row--selected):hover {
                    background-color: transparent !important; 
                }

                .mdc-data-table {
       
                }

                .table-container {
                    min-height: 300px;
                    height: 50vh;
                    max-height: 70vh;
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
                
                }

                .state-label.enabled {
                    border: 1px solid var(--or-app-color3, ${unsafeCSS(Colors.DefaultColor4)});
                    color: var(--or-app-color3, ${unsafeCSS(Colors.DefaultColor4)});
                }

                .state-label.disabled {
                    border: 1px solid var(--or-app-color4, ${unsafeCSS(Colors.DefaultColor4)});
                    background-color: var(--or-app-color4, ${unsafeCSS(Colors.DefaultColor4)});
                }

  
            `
        ] as any; // Cast to bypass strict type check by OrMwcTable extension
    }

    @property({ type: Array })
    public modelConfigs: ModelConfig[] = [];

    public columns: TableColumn[] = [
        { title: "State", isSortable: true },
        { title: "Name", isSortable: true },
        { title: "Type", isSortable: true },
        { title: "Asset ID", isSortable: true },
        { title: "Attribute Name", isSortable: true },
        { title: "Actions", isSortable: false }
    ];

    protected config: TableConfig = {
        stickyFirstColumn: false,
    };

    private getStateRowTemplate(config: ModelConfig): TemplateResult {
        return html`<span class="state-label ${config.enabled ? 'enabled' : 'disabled'}">${config.enabled ? 'Enabled' : 'Disabled'}</span>`;
    }

    private getActionsRowTemplate(config: ModelConfig): TemplateResult {
        const handleEdit = (e: Event) => {
            e.stopPropagation();
            this.dispatchEvent(new CustomEvent('edit-config', { detail: config, bubbles: true, composed: true }));
        };

        const handleDelete = (e: Event) => {
            e.stopPropagation();
            this.dispatchEvent(new CustomEvent('delete-config', { detail: config, bubbles: true, composed: true }));
        };

        return html`
            <div class="actions-container">
                <or-mwc-input type="${InputType.BUTTON}" outlined icon="pencil" label="Edit" @click="${handleEdit}"></or-mwc-input>
                <or-mwc-input type="${InputType.BUTTON}" outlined icon="delete" style="margin-left: 10px;" label="Delete" @click="${handleDelete}"></or-mwc-input>
            </div>
        `;
    }

    protected getTableRows(configs: ModelConfig[]): TableRow[] {
        return configs.map(config => ({
            content: [
                this.getStateRowTemplate(config) as any,
                config.name,
                config.type.charAt(0).toUpperCase() + config.type.slice(1), // Capitalize first letter
                config.target.asset_id,
                config.target.attribute_name,
                this.getActionsRowTemplate(config) as any
            ]
        }));
    }

    protected getNoDataSectionTemplate(): TemplateResult {
        if (this.modelConfigs.length === 0) {
            return html`
            <div class="no-data-section">
                <div>No forecast configurations found.</div>
                <or-mwc-input type="${InputType.BUTTON}" outlined icon="plus" label="Configure new forecast" @click="${this.handleAddConfig}"></or-mwc-input>
            </div>`;
        }

        return html``;
    }

    private handleAddConfig() {
        const realm = getRealm(window.location.pathname);
        Router.go(`/${realm}/configs/new`);
    }

    render() {
        return html`
            <div class="table-container">
                ${super.render()}
                ${this.getNoDataSectionTemplate()}
            </div>
        `;
    }

    protected willUpdate(changedProperties: Map<string, any>): void {
        if (changedProperties.has('modelConfigs')) {
            this.rows = this.getTableRows(this.modelConfigs);
        }
        super.willUpdate(changedProperties);
    }


}
