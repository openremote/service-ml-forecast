import { css, html, LitElement } from 'lit'
import { customElement } from 'lit/decorators.js'

@customElement('page-service-unavailable')
export class PageServiceUnavailable extends LitElement {
    static get styles() {
        return css`
            :host {
                width: fit-content;
            }

            .container {
                text-align: center;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
            }

            .title {
                font-size: 36px;
                display: flex;
                align-items: center;
                gap: 10px;
                font-weight: bold;
                margin-bottom: 0px;
                color: var(--or-app-color3);
            }

            .subtitle {
                font-size: 16px;
                color: var(--or-app-color3);
            }
        `
    }

    render() {
        return html`
            <div class="container">
                <h1 class="title"><or-icon style="font-size: 36px;" icon="alert-box-outline"></or-icon> Service unavailable</h1>
                <p class="subtitle">The service is currently unavailable. Please try again later.</p>
            </div>
        `
    }
}
