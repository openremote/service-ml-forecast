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

import { OrAssetAttributePicker } from '@openremote/or-attribute-picker';
import { customElement, property } from 'lit/decorators.js';
import { WellknownMetaItems } from '@openremote/model';
import manager, { DefaultColor5, Util } from '@openremote/core';
import { OrAssetTree, OrAssetTreeSelectionEvent } from '@openremote/or-asset-tree';
import { css, html, unsafeCSS } from 'lit';
import { when } from 'lit/directives/when.js';
import { until } from 'lit/directives/until.js';

/**
 * Extended version of the default or-asset-attribute-picker component.
 * Adds the ability to filter on hasPredictedDataPoints
 */
@customElement('custom-asset-attribute-picker')
export class CustomAssetAttributePicker extends OrAssetAttributePicker {
    static get styles() {
        return [
            ...(Array.isArray(super.styles) ? super.styles : [super.styles]),

            // Scrim doesn't properly work when embedded in an iframe
            css`
                .mdc-dialog .mdc-dialog__scrim {
                    background-color: transparent !important;
                }
            `
        ];
    }
    @property({ type: Boolean })
    public showOnlyHasPredictedDatapointsAttrs = false;

    public setShowOnlyHasPredictedDatapointsAttrs(value: boolean): this {
        this.showOnlyHasPredictedDatapointsAttrs = value;
        return this;
    }

    protected _getNoAttributesMessage(): string {
        if (this.showOnlyHasPredictedDatapointsAttrs && this.showOnlyDatapointAttrs) {
            // TODO: local translation
            return "No attributes with 'has predicted data points' and either 'store data points' or 'agent link' configuration item found";
        }
        if (this.showOnlyHasPredictedDatapointsAttrs) {
            // TODO: local translation
            return "No attributes with 'has predicted data points' configuration item found";
        }
        if (this.showOnlyDatapointAttrs && this.showOnlyRuleStateAttrs) {
            return 'noDatapointsOrRuleStateAttributes';
        }
        if (this.showOnlyDatapointAttrs) {
            return 'noDatapointsAttributes';
        }
        if (this.showOnlyRuleStateAttrs) {
            return 'noRuleStateAttributes';
        }
        return 'noAttributesToShow';
    }

    /**
     * Duplicated method from the component source code, so we can override it and add our own filtering logic.
     */
    protected async _onAssetSelectionChanged(event: OrAssetTreeSelectionEvent) {
        this._assetAttributes = undefined;
        if (!this.multiSelect) {
            this.selectedAttributes = [];
        }
        this.addBtn.disabled = this.selectedAttributes.length === 0;
        const assetTree = event.target as OrAssetTree;
        assetTree.disabled = true;

        let selectedAsset = event.detail.newNodes.length === 0 ? undefined : event.detail.newNodes[0].asset;
        this._asset = selectedAsset;

        if (selectedAsset) {
            const assetResponse = await manager.rest.api.AssetResource.get(selectedAsset.id!);
            selectedAsset = assetResponse.data;

            if (selectedAsset) {
                this._assetAttributes = Object.values(selectedAsset.attributes!)
                    .map((attr) => ({ ...attr, id: selectedAsset!.id! }))
                    .sort(Util.sortByString((attribute) => attribute.name!));

                if (this.attributeFilter) {
                    this._assetAttributes = this._assetAttributes.filter((attr) => this.attributeFilter!(attr));
                }

                // Filter by predicted datapoints + datapoints (requires hasPredictedDataPoints and (storeDataPoints or agentLink))
                if (this.showOnlyHasPredictedDatapointsAttrs && this.showOnlyDatapointAttrs) {
                    this._assetAttributes = this._assetAttributes.filter(
                        (e) =>
                            e.meta?.[WellknownMetaItems.HASPREDICTEDDATAPOINTS] &&
                            (e.meta?.[WellknownMetaItems.STOREDATAPOINTS] || e.meta?.[WellknownMetaItems.AGENTLINK])
                    );
                } else if (this.showOnlyHasPredictedDatapointsAttrs) {
                    this._assetAttributes = this._assetAttributes.filter((e) => e.meta?.[WellknownMetaItems.HASPREDICTEDDATAPOINTS]);
                } else if (this.showOnlyDatapointAttrs && this.showOnlyRuleStateAttrs) {
                    this._assetAttributes = this._assetAttributes.filter(
                        (e) =>
                            e.meta &&
                            (e.meta[WellknownMetaItems.STOREDATAPOINTS] ||
                                e.meta[WellknownMetaItems.RULESTATE] ||
                                e.meta[WellknownMetaItems.AGENTLINK])
                    );
                } else if (this.showOnlyDatapointAttrs) {
                    this._assetAttributes = this._assetAttributes.filter(
                        (e) => e.meta && (e.meta[WellknownMetaItems.STOREDATAPOINTS] || e.meta[WellknownMetaItems.AGENTLINK])
                    );
                } else if (this.showOnlyRuleStateAttrs) {
                    this._assetAttributes = this._assetAttributes.filter(
                        (e) => e.meta && (e.meta[WellknownMetaItems.RULESTATE] || e.meta[WellknownMetaItems.AGENTLINK])
                    );
                }
            }
        }
        assetTree.disabled = false;
    }

    /**
     * Duplicated method from the component source code, so we can override it and add additional content.
     */
    protected _setDialogContent(): void {
        this.content = () => html`
            <div class="row" style="display: flex;height: 600px;width: 800px;border-top: 1px solid ${unsafeCSS(DefaultColor5)};">
                <div class="col" style="width: 260px;overflow: auto;border-right: 1px solid ${unsafeCSS(DefaultColor5)};">
                    <or-asset-tree
                        id="chart-asset-tree"
                        readonly
                        .selectedIds="${this.selectedAssets.length > 0 ? this.selectedAssets : null}"
                        @or-asset-tree-selection="${(ev: OrAssetTreeSelectionEvent) => this._onAssetSelectionChanged(ev)}"
                    >
                    </or-asset-tree>
                </div>
                <div class="col" style="flex: 1 1 auto;width: 260px;overflow: auto;">
                    ${when(
                        this._assetAttributes && this._assetAttributes.length > 0,
                        () => {
                            const selectedNames = this.selectedAttributes
                                .filter((attrRef) => attrRef.id === this._asset?.id)
                                .map((attrRef) => attrRef.name!);
                            return html`
                                <div class="attributes-header">
                                    <or-translate value="attribute_plural"></or-translate>
                                </div>
                                ${until(
                                    this._getAttributesTemplate(
                                        this._assetAttributes,
                                        undefined,
                                        selectedNames,
                                        this.multiSelect,
                                        (attrNames) => this._onAttributesSelect(attrNames)
                                    ),
                                    html`<or-loading></or-loading>`
                                )}
                            `;
                        },
                        () => html`
                            <div style="display: flex;align-items: center;text-align: center;height: 100%;padding: 0 20px;">
                                <span style="width:100%">
                                    <or-translate
                                        value="${this._assetAttributes && this._assetAttributes.length === 0
                                            ? this._getNoAttributesMessage()
                                            : 'selectAssetOnTheLeft'}"
                                    >
                                    </or-translate>
                                </span>
                            </div>
                        `
                    )}
                </div>
            </div>
        `;
    }
}
