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
import { customElement, property } from 'lit/decorators.js';
import { InputType, OrInputChangedEvent } from '@openremote/or-mwc-components/or-mwc-input';

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
export class CustomDurationInput extends LitElement {
    static get styles() {
        return css`
            :host {
                display: block;
            }
        `;
    }

    connectedCallback() {
        super.connectedCallback();

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

    onInput(e: OrInputChangedEvent) {
        const value = e.detail.value;
        const target = e.target as HTMLInputElement;

        if (!target || value === undefined) {
            return;
        }

        switch (target.name) {
            case 'value':
                this.number = value;
                break;
            case 'unit':
                this.unit = value;
                break;
        }

        if (!this.unit || !this.number) {
            return;
        }

        // Replace the % in the unit with the number and set the value
        switch (this.type) {
            case DurationInputType.ISO_8601:
                this.value = `${this.unit.replace('%', this.number.toString())}`;
                break;
            case DurationInputType.PANDAS_FREQ:
                this.value = `${this.unit.replace('%', this.number.toString())}`;
        }

        // Fire event to notify parent component that the value has changed
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
        return unit as TimeDurationUnit;
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
        return unit as PandasTimeUnit;
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
            <or-mwc-input
                type="${InputType.NUMBER}"
                name="value"
                .value=${this.number}
                @or-mwc-input-changed=${this.onInput}
                label=${this.label}
            ></or-mwc-input>
            <or-mwc-input
                type="${InputType.SELECT}"
                name="unit"
                label="Unit"
                .value=${this.unit}
                @or-mwc-input-changed=${this.onInput}
                .options="${this.getUnitOptions()}"
            ></or-mwc-input>
        `;
    }
}
