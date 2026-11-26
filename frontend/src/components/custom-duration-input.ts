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

import { css, html, type PropertyValues } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { OrElement } from '@openremote/or-element';
import '@openremote/or-vaadin-components/or-vaadin-number-field';
import '@openremote/or-vaadin-components/or-vaadin-select';
import type { OrVaadinNumberField } from '@openremote/or-vaadin-components/or-vaadin-number-field';
import type { OrVaadinSelect } from '@openremote/or-vaadin-components/or-vaadin-select';

// Duration Input Type
export enum DurationInputType {
    ISO_8601 = 'ISO_8601',
    PANDAS_FREQ = 'PANDAS_FREQ'
}

// ISO 8601
export enum TimeDurationUnit {
    MINUTE = 'PT%M',
    HOUR = 'PT%H',
    DAY = 'P%D',
    WEEK = 'P%W',
    MONTH = 'P%M',
    YEAR = 'P%Y'
}

// Display name for the ISO 8601 units
const TimeDurationUnitDisplay: Record<TimeDurationUnit, string> = {
    [TimeDurationUnit.MINUTE]: 'Minutes',
    [TimeDurationUnit.HOUR]: 'Hours',
    [TimeDurationUnit.DAY]: 'Days',
    [TimeDurationUnit.WEEK]: 'Weeks',
    [TimeDurationUnit.MONTH]: 'Months',
    [TimeDurationUnit.YEAR]: 'Years'
};

// Pandas Frequency
export enum PandasTimeUnit {
    MINUTE = '%min',
    HOUR = '%h'
}

// Display name for the Pandas units
const PandasTimeUnitDisplay: Record<PandasTimeUnit, string> = {
    [PandasTimeUnit.MINUTE]: 'Minutes',
    [PandasTimeUnit.HOUR]: 'Hours'
};

// This is a input component that renders both a number input and a dropdown for the unit of the duration
@customElement('custom-duration-input')
export class CustomDurationInput extends OrElement {
    static get styles() {
        return css`
            :host {
                display: grid;
                grid-template-columns: minmax(0, 1fr) minmax(6rem, 0.55fr);
                gap: var(--lumo-space-xs, 4px);
                align-items: start;
            }

            or-vaadin-number-field,
            or-vaadin-select {
                width: 100%;
                min-width: 0;
            }

            or-vaadin-select {
                padding-top: calc(var(--lumo-font-size-s) * 1.5);
            }

            or-vaadin-number-field::part(label) {
                white-space: normal;
                line-height: 1;
            }

            .unit-label {
                position: absolute;
                width: 1px;
                height: 1px;
                overflow: hidden;
                clip-path: inset(50%);
                white-space: nowrap;
            }
        `;
    }

    protected willUpdate(changed: PropertyValues) {
        if (!changed.has('value') && !changed.has('type')) return;
        if (this.value === this.lastInputValue && !changed.has('type')) return;

        switch (this.type) {
            case DurationInputType.ISO_8601:
                this.number = this.getNumberFromDuration(this.value);
                this.unit = this.getUnitFromDuration(this.value);
                break;
            case DurationInputType.PANDAS_FREQ:
                this.number = this.getNumberFromPandasFrequency(this.value);
                this.unit = this.getUnitFromPandasFrequency(this.value);
        }
    }

    onInput(event: Event) {
        const target = event.currentTarget as OrVaadinNumberField | OrVaadinSelect;
        const value = target.value;

        switch (target.name) {
            case 'value': {
                const number = value === '' ? null : Number(value);
                if (this.number === number) return;
                this.number = number;
                break;
            }
            case 'unit':
                if (this.unit === (value || null)) return;
                this.unit = (value || null) as TimeDurationUnit | PandasTimeUnit | null;
                break;
        }

        this.value = this.checkValidity() && this.unit ? this.unit.replace('%', String(this.number)) : '';
        this.lastInputValue = this.value;
        this.requestUpdate();
        this.dispatchEvent(new CustomEvent('value-changed', { detail: { value: this.value, name: this.name } }));
    }

    @property({ type: String })
    public label: string = '';

    @property({ type: String })
    public name: string = '';

    // Passed in from the parent component
    @property({ type: String })
    public type: DurationInputType = DurationInputType.ISO_8601;

    // The value passed should be PT1H or 1h for example, the unit will be inferred from the value
    @property({ type: String })
    public value: string = '';

    @property({ type: Array })
    public iso_units: TimeDurationUnit[] = [TimeDurationUnit.MINUTE, TimeDurationUnit.HOUR];

    @property({ type: Array })
    public pandas_units: PandasTimeUnit[] = [PandasTimeUnit.MINUTE, PandasTimeUnit.HOUR];

    protected number: number | null = null;

    protected unit: TimeDurationUnit | PandasTimeUnit | null = null;

    protected lastInputValue?: string;

    checkValidity(): boolean {
        return (
            Number.isInteger(Number(this.number)) && Number(this.number) >= 1 && this.getUnitOptions().some(([unit]) => unit === this.unit)
        );
    }

    // Extract the number from the ISO 8601 Duration string
    getNumberFromDuration(duration: string): number | null {
        const match = /P(?:T)?(\d+)([HMDWMOY]+)/.exec(duration);
        return match ? parseInt(match[1], 10) : null;
    }

    // Extract the unit from the ISO 8601 Duration string
    getUnitFromDuration(duration: string): TimeDurationUnit | null {
        const match = /P(?:T)?(\d+)([HMDWMOY]+)/.exec(duration);

        // replace the number in the full match with % to get the unit
        const unit = match?.[0]?.replace(match?.[1], '%');
        return (unit as TimeDurationUnit | undefined) ?? null;
    }

    // Extract the number from the Pandas Frequency string
    getNumberFromPandasFrequency(freq: string): number | null {
        const match = /(\d+)(min|h)/.exec(freq);
        return match ? parseInt(match[1], 10) : null;
    }

    // Extract the unit from the Pandas Frequency string
    getUnitFromPandasFrequency(freq: string): PandasTimeUnit | null {
        const match = /(\d+)(min|h)/.exec(freq);

        // replace the number in the full match with % to get the unit
        const unit = match?.[0]?.replace(match?.[1], '%');
        return (unit as PandasTimeUnit | undefined) ?? null;
    }

    // Get available unit options based on the units property or defaults
    getUnitOptions(): [string, string][] {
        if (this.type === DurationInputType.ISO_8601) {
            return this.iso_units.map((unit) => [unit, TimeDurationUnitDisplay[unit]]);
        } else if (this.type === DurationInputType.PANDAS_FREQ) {
            return this.pandas_units.map((unit) => [unit, PandasTimeUnitDisplay[unit]]);
        }

        return [];
    }

    render() {
        // if type is unknown, render unsupported type message
        if (!(this.type in DurationInputType)) {
            return html`<div>Unsupported type</div>`;
        }

        return html`
            <or-vaadin-number-field
                name="value"
                .value=${this.number === null ? '' : String(this.number)}
                @value-changed=${this.onInput}
                label=${this.label}
                min="1"
                step="1"
                required
                .invalid=${!this.checkValidity()}
                error-message="Enter a whole number of at least 1 and choose a unit."
            ></or-vaadin-number-field>
            <span id="unit-label" class="unit-label">${this.label} unit</span>
            <or-vaadin-select
                name="unit"
                accessible-name-ref="unit-label"
                .value=${this.unit ?? ''}
                @value-changed=${this.onInput}
                .items=${this.getUnitOptions().map(([value, label]) => ({ value, label }))}
                required
            ></or-vaadin-select>
        `;
    }
}
