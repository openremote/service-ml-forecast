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

import { css, html, type PropertyValues } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { OrElement } from '@openremote/or-element';
import '@openremote/or-vaadin-components/or-vaadin-text-field';
import type { OrVaadinTextField } from '@openremote/or-vaadin-components/or-vaadin-text-field';

export function parseCovariateLags(text: string, role: 'past' | 'future'): number | number[] {
    const value: unknown = JSON.parse(text);
    if (role === 'past' && Number.isInteger(value) && (value as number) > 0) return value as number;
    if (
        Array.isArray(value) &&
        value.length > 0 &&
        value.every((v) => typeof v === 'number' && Number.isInteger(v) && (role === 'past' ? v < 0 : v >= 0))
    ) {
        return value as number[];
    }
    throw new Error(
        role === 'past'
            ? 'Use a positive count, such as 24, or negative steps, such as [-24].'
            : 'Use a list of zero or positive steps, such as [0] or [0, 1].'
    );
}

@customElement('covariate-lags-input')
export class CovariateLagsInput extends OrElement {
    @property() name = '';
    @property() label = 'Regressor lags (steps)';
    @property({ attribute: false }) value: number | number[] | null | undefined;
    @property() role: 'past' | 'future' = 'future';
    @state() private draft = '';
    @state() private error = '';

    static styles = css`
        :host {
            display: block;
            max-width: 350px;
        }

        or-vaadin-text-field {
            width: 100%;
            min-width: 0;
        }
    `;

    protected willUpdate(changed: PropertyValues) {
        if (changed.has('value') || changed.has('role')) {
            this.draft = this.value == null ? '' : JSON.stringify(this.value);
            this.error = '';
        }
    }

    checkValidity(): boolean {
        try {
            parseCovariateLags(this.draft, this.role);
            return true;
        } catch {
            return false;
        }
    }

    private onInput(event: Event) {
        this.draft = (event.currentTarget as OrVaadinTextField).value;
        let value: number | number[] | null = null;
        try {
            value = parseCovariateLags(this.draft, this.role);
            this.error = '';
        } catch {
            this.error =
                this.role === 'past'
                    ? 'Enter a positive count or negative steps, for example 24 or [-24].'
                    : 'Enter zero or positive steps in brackets, for example [0].';
        }
        this.requestUpdate();
        this.dispatchEvent(
            new CustomEvent('value-changed', {
                detail: { value, valid: !this.error },
                bubbles: true,
                composed: true
            })
        );
    }

    protected render() {
        return html`<or-vaadin-text-field
            label=${this.label}
            .value=${this.draft}
            helper-text=${this.role === 'past'
                ? 'Count or negative steps, e.g. 24 or [-24].'
                : '[0] uses the forecast timestamp; positive steps require later values.'}
            .invalid=${!!this.error}
            .errorMessage=${this.error}
            manual-validation
            @input=${this.onInput}
            required
        ></or-vaadin-text-field>`;
    }
}
