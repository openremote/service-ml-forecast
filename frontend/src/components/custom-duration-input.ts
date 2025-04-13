import { css, html, LitElement } from 'lit'
import { customElement, property, state } from 'lit/decorators.js'
import '@openremote/or-mwc-components/or-mwc-input'
import { InputType, OrInputChangedEvent } from '@openremote/or-mwc-components/or-mwc-input'

// Duration Input Type
export enum DurationInputType {
    ISO_8601 = 'ISO_8601',
    PANDAS_FREQ = 'PANDAS_FREQ'
}

// ISO 8601
enum TimeDurationUnit {
    MINUTE = 'M',
    HOUR = 'H'
}

// Pandas Frequency
enum PandasTimeUnit {
    MINUTE = 'min',
    HOUR = 'h'
}

// This is a input component that renders both a number input and a dropdown for the unit of the duration
@customElement('custom-duration-input')
export class CustomDurationInput extends LitElement {
    static get styles() {
        return css`
            :host {
                display: block;
            }
        `
    }

    connectedCallback() {
        super.connectedCallback()

        switch (this.type) {
            case DurationInputType.ISO_8601:
                this.number = this.getNumberFromDuration(this.value)
                this.unit = this.getUnitFromDuration(this.value)
                break
            case DurationInputType.PANDAS_FREQ:
                this.number = this.getNumberFromPandasFrequency(this.value)
                this.unit = this.getUnitFromPandasFrequency(this.value)
        }
    }

    onInput(e: OrInputChangedEvent) {
        const value = e.detail.value
        const target = e.target as HTMLInputElement

        if (!target || value === undefined) {
            return
        }

        switch (target.name) {
            case 'value':
                this.number = value
                break
            case 'unit':
                this.unit = value
                break
        }

        switch (this.type) {
            case DurationInputType.ISO_8601:
                this.value = `PT${this.number}${this.unit}`
                break
            case DurationInputType.PANDAS_FREQ:
                this.value = `${this.number}${this.unit}`
        }

        // Fire event to notify parent component that the value has changed
        this.dispatchEvent(new CustomEvent('value-changed', { detail: { value: this.value, name: this.name } }))
    }

    @property({ type: String })
    public label: string = ''

    @property({ type: String })
    public name: string = ''

    // Passed in from the parent component
    @property({ type: String })
    public type: DurationInputType = DurationInputType.ISO_8601

    // The value passed should be PT1H or 1h for example, the unit will be inferred from the value
    @property({ type: String })
    public value: string = ''

    @state()
    private number: number | null = null

    @state()
    private unit: TimeDurationUnit | PandasTimeUnit | null = null

    // Extract the number from the ISO 8601 Duration string
    getNumberFromDuration(duration: string): number | null {
        const match = /PT(\d+)([HM])/.exec(duration)
        return match ? parseInt(match[1], 10) : null
    }

    // Extract the unit from the ISO 8601 Duration string
    getUnitFromDuration(duration: string): TimeDurationUnit {
        const match = /PT(\d+)([HM])/.exec(duration)
        return match ? (match[2] as TimeDurationUnit) : null
    }

    // Extract the number from the Pandas Frequency string
    getNumberFromPandasFrequency(freq: string): number | null {
        const match = /(\d+)(min|h)/.exec(freq)
        return match ? parseInt(match[1], 10) : null
    }

    // Extract the unit from the Pandas Frequency string
    getUnitFromPandasFrequency(freq: string): PandasTimeUnit {
        const match = /(\d+)(min|h)/.exec(freq)
        return match ? (match[2] as PandasTimeUnit) : null
    }

    render() {
        // if type is unknown, render unsupported type message
        if (!(this.type in DurationInputType)) {
            return html`<div>Unsupported type</div>`
        }

        return html`
            <div>
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
                    .options="${this.type === DurationInputType.ISO_8601
                        ? [
                              [TimeDurationUnit.MINUTE, 'Minutes'],
                              [TimeDurationUnit.HOUR, 'Hours']
                          ]
                        : [
                              [PandasTimeUnit.MINUTE, 'Minutes'],
                              [PandasTimeUnit.HOUR, 'Hours']
                          ]}"
                ></or-mwc-input>
            </div>
        `
    }
}
