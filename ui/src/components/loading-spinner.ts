import { css, html, LitElement } from "lit";
import { customElement } from "lit/decorators.js";


@customElement("loading-spinner")
export class LoadingSpinner extends LitElement {

    static get styles() {
        return css`
            :host {
                display: flex;
                justify-content: center;
                align-items: center;
            }

            .loading-spinner {
                display: flex;
                justify-content: center;
                align-items: center;
                width: 50px;
                height: 100px;
            }

            img {
                width: 50px;
                height: 50px;
            }

            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }

            @keyframes fade {
                0% { opacity: 0; }
                100% { opacity: 1; }
            }

            img {
                animation: spin 1s linear infinite, fade 0.5s ease-in-out;
            }
        `;
    }

    render() {
        return html`<span class="loading-spinner"><img src="/static/images/logo.svg" alt="" /></span>`;
    }
}