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

import { css, html, LitElement } from 'lit'
import { customElement } from 'lit/decorators.js'
import { getRootPath } from '../util'

@customElement('loading-spinner')
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
                0% {
                    transform: rotate(0deg);
                }
                100% {
                    transform: rotate(360deg);
                }
            }

            @keyframes fade {
                0% {
                    opacity: 0;
                }
                100% {
                    opacity: 1;
                }
            }

            img {
                animation:
                    spin 1s linear infinite,
                    fade 0.5s ease-in-out;
            }
        `
    }

    private readonly rootPath = getRootPath()

    render() {
        return html`<span class="loading-spinner"><img src="${this.rootPath}/assets/images/logo.svg" alt="" /></span>`
    }
}
