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
import { customElement } from 'lit/decorators.js';

@customElement('page-not-found')
export class PageNotFound extends LitElement {
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
        `;
    }

    render() {
        return html`
            <div class="container">
                <h1 class="title"><or-icon style="font-size: 36px;" icon="alert-box-outline"></or-icon> Page not found</h1>
                <p class="subtitle">The page you are looking for does not exist.</p>
            </div>
        `;
    }
}
