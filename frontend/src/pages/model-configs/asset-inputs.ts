// Copyright 2026, OpenRemote Inc.
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

import { html } from 'lit';
import { map } from 'lit/directives/map.js';
import { guard } from 'lit/directives/guard.js';
import '@openremote/or-vaadin-components/or-vaadin-combo-box';
import '@openremote/or-vaadin-components/or-vaadin-button';
import type { OrVaadinComboBox } from '@openremote/or-vaadin-components/or-vaadin-combo-box';
import { RegressorFeature } from '../../services/models';
import type { ModelTypeConfig } from './model-registry';
import { DurationInputType, TimeDurationUnit } from '../../components/custom-duration-input';
import '../../components/covariate-lags-input';

type InputContext = Parameters<ModelTypeConfig['getCovariatesTemplate']>[1];

/** Shared controls keep Prophet regressors and tree covariates consistent. */
export function assetInputs(options: {
    title: string;
    description: string;
    features: RegressorFeature[] | null | undefined;
    context: InputContext;
    onChange: (features: RegressorFeature[] | null) => void;
    role: 'past' | 'future';
    lags?: number | number[] | null;
    onLags?: (value: number | number[]) => void;
}) {
    const { context } = options;
    const commit = (features: RegressorFeature[]) => {
        options.onChange(features.length ? features : null);
        context.requestUpdate();
    };
    const change = (event: Event, index: number) => {
        const target = event.currentTarget as HTMLInputElement | OrVaadinComboBox;
        const field = target.name;
        const value = event.type === 'change' ? target.value : (event as CustomEvent<{ value: string }>).detail?.value;
        if (value === undefined) return;
        const features = [...(options.features ?? [])];
        const current = { ...features[index], [field]: value };
        if (field === 'asset_id') {
            current.attribute_name =
                context.attributeSelectList
                    .get(value as string)
                    ?.keys()
                    .next().value ?? '';
        }
        features[index] = current;
        commit(features);
    };
    return html`<details class="config-group" open>
        <summary>${options.title}</summary>
        <div class="group-content">
            <div class="column">
                <p class="input-help">${options.description}</p>
                ${map(
                    options.features ?? [],
                    (feature, index) =>
                        html` <div class="regressor-row">
                            <div class="row">
                                <or-vaadin-combo-box
                                    name="asset_id"
                                    label="Asset"
                                    item-label-path="label"
                                    item-value-path="value"
                                    .items=${guard([context.assetSelectList], () =>
                                        [...context.assetSelectList].map(([value, label]) => ({ value, label }))
                                    )}
                                    .value=${feature.asset_id}
                                    @change=${(e: Event) => change(e, index)}
                                    clear-button-visible
                                    required
                                ></or-vaadin-combo-box>
                                <or-vaadin-combo-box
                                    name="attribute_name"
                                    label="Attribute"
                                    item-label-path="label"
                                    item-value-path="value"
                                    .items=${guard([context.attributeSelectList, feature.asset_id], () =>
                                        [...(context.attributeSelectList.get(feature.asset_id) ?? new Map())].map(([value, label]) => ({
                                            value,
                                            label
                                        }))
                                    )}
                                    .value=${feature.attribute_name}
                                    ?disabled=${!feature.asset_id}
                                    @change=${(e: Event) => change(e, index)}
                                    clear-button-visible
                                    required
                                ></or-vaadin-combo-box>
                                <custom-duration-input
                                    name="training_data_period"
                                    label="Training data period"
                                    .type=${DurationInputType.ISO_8601}
                                    .iso_units=${[
                                        TimeDurationUnit.DAY,
                                        TimeDurationUnit.WEEK,
                                        TimeDurationUnit.MONTH,
                                        TimeDurationUnit.YEAR
                                    ]}
                                    .value=${feature.training_data_period}
                                    @value-changed=${(e: Event) => change(e, index)}
                                ></custom-duration-input>
                                <or-vaadin-button
                                    theme="tertiary error"
                                    @click=${() => commit((options.features ?? []).filter((_, i) => i !== index))}
                                >
                                    <or-icon icon="delete" aria-hidden="true"></or-icon>Remove
                                </or-vaadin-button>
                            </div>
                        </div>`
                )}
                ${options.onLags && options.features?.length
                    ? html` <covariate-lags-input
                          .value=${options.lags}
                          .role=${options.role}
                          @value-changed=${(e: CustomEvent) => {
                              if (e.detail.valid) options.onLags?.(e.detail.value);
                              context.requestUpdate();
                          }}
                      ></covariate-lags-input>`
                    : html``}
                <or-vaadin-button
                    class="regressor-add"
                    theme="tertiary"
                    @click=${() =>
                        commit([
                            ...(options.features ?? []),
                            {
                                asset_id: '',
                                attribute_name: '',
                                training_data_period: 'P6M'
                            }
                        ])}
                >
                    <or-icon icon="plus" aria-hidden="true"></or-icon>Add regressor
                </or-vaadin-button>
            </div>
        </div>
    </details>`;
}
