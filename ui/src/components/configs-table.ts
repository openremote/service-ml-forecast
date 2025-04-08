import { OrMwcTable, TableColumn, TableRow, TableConfig } from "@openremote/or-mwc-components/or-mwc-table";
import { css, html, TemplateResult } from "lit";
import { customElement, property } from "lit/decorators.js";
import { ModelConfig } from "../api/models";
import { ServiceClient } from "../api/service-client";
import "@openremote/or-mwc-components/or-mwc-input";

@customElement("configs-table")
export class ConfigsTable extends OrMwcTable {

    @property({ type: Array })
    private modelConfigs: ModelConfig[] = [];

    private readonly serviceClient: ServiceClient = new ServiceClient();

    public columns: TableColumn[] = [
        { title: "State", isSortable: true },
        { title: "Name", isSortable: true },
        { title: "Realm", isSortable: true },
        { title: "Type", isSortable: true },
        { title: "Asset ID", isSortable: true },
        { title: "Attribute Name", isSortable: true },
        { title: "Actions", isSortable: false }
    ];

    protected config: TableConfig = {
        stickyFirstColumn: false,
    };

    connectedCallback() {
        super.connectedCallback();
        this.fetchConfigs();
    }

    static get styles() {
        return [
            super.styles,
            css`
                /* Override default row hover background */
                .mdc-data-table__row:not(.mdc-data-table__row--selected):hover {
                    background-color: transparent !important; /* Or your desired color */
                }
            `
        ] as any; // Cast to bypass strict type check by OrMwcTable extension
    }

    fetchConfigs() {
        this.serviceClient.getModelConfigs().then(configs => {
            this.modelConfigs = configs;
        });
    }

    private getStateRow(config: ModelConfig): TemplateResult {
        const state = config.enabled ? 'Enabled' : 'Disabled';
        const style = config.enabled ? 'color: green;' : 'color: red;';
        return html`<span style="${style}">${state}</span>`;
    }

    private getActionsRow(config: ModelConfig): TemplateResult {
        const handleEdit = (e: Event) => {
            e.stopPropagation();
            this.dispatchEvent(new CustomEvent('edit-config', { detail: config, bubbles: true, composed: true }));
        };

        const handleDelete = (e: Event) => {
            e.stopPropagation();
            this.dispatchEvent(new CustomEvent('delete-config', { detail: config, bubbles: true, composed: true }));
        };

        return html`
            <or-mwc-input type="button" outlined icon="pencil" label="Edit" @click="${handleEdit}"></or-mwc-input>
            <or-mwc-input type="button" outlined icon="delete" style="margin-left: 10px;" label="Delete" @click="${handleDelete}"></or-mwc-input>
        `;
    }

    protected getTableRows(configs: ModelConfig[]): TableRow[] {
        return configs.map(config => ({
            content: [
                this.getStateRow(config) as any,
                config.name,
                config.realm,
                config.type,
                config.target.asset_id,
                config.target.attribute_name,
                this.getActionsRow(config) as any
            ]
        }));
    }

    protected willUpdate(changedProperties: Map<string, any>): void {
        if (changedProperties.has('modelConfigs')) {
            this.rows = this.getTableRows(this.modelConfigs);
        }

        super.willUpdate(changedProperties);
    }
}
