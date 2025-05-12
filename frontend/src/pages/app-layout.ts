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

import { createContext, provide } from '@lit/context';
import { Router, RouterLocation } from '@vaadin/router';
import { html, LitElement } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { getRootPath } from '../common/util';
import '../components/breadcrumb-nav';
import '../components/loading-spinner';
import { AuthService } from '../services/auth-service';
import { setRealmTheme } from '../common/theme';

export const context = createContext<string>(Symbol('realm'));

@customElement('app-layout')
export class AppLayout extends LitElement {
    @provide({ context })
    @state()
    realm = '';

    @state()
    private authenticated = false;

    private readonly rootPath = getRootPath();

    async onBeforeEnter(location: RouterLocation) {
        // Try and get realm via location params before entering the route
        const realm = location.params.realm as string;
        this.realm = realm;

        // Fallback to authservice if param is not provided
        if (!this.realm) {
            this.realm = AuthService.realm;
            console.log('No realm param provided, falling back to auth realm:', this.realm);
            Router.go(`${this.rootPath}/${this.realm}`);
        }

        // Update the app with the realm theme
        await setRealmTheme(this.realm);

        // Listen for auth changes
        this.authenticated = AuthService.authenticated;
        AuthService.subscribe(() => {
            this.authenticated = AuthService.authenticated;
        });
    }

    render() {
        if (!this.authenticated) {
            return html` <loading-spinner></loading-spinner> `;
        }

        return html`
            <breadcrumb-nav realm=${this.realm}></breadcrumb-nav>
            <slot></slot>
        `;
    }
}
