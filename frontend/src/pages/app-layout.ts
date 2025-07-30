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
import { PreventAndRedirectCommands, RouterLocation } from '@vaadin/router';
import { css, html, LitElement, unsafeCSS } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { setRealmTheme } from '../common/theme';
import { AuthService } from '../services/auth-service';
import { manager } from '@openremote/core';
import { IS_EMBEDDED, ML_OR_URL } from '../common/constants';

export const realmContext = createContext<string>(Symbol('realm'));

@customElement('app-layout')
export class AppLayout extends LitElement {
    static get styles() {
        const padding = IS_EMBEDDED ? '0 20px' : '20px';

        return css`
            :host {
                display: block;
                padding: ${unsafeCSS(padding)};
            }
        `;
    }

    @provide({ context: realmContext })
    @state()
    realm = '';

    // Called before the initial Vaadin Router location is entered ('/'), only called once since its a parent route
    async onBeforeEnter(location: RouterLocation, commands: PreventAndRedirectCommands) {
        if (!AuthService.authenticated) {
            await AuthService.login();
            return;
        }

        const paramRealm = location.params.realm as string;
        const authRealm = AuthService.realm;

        // Param realm takes precedence over auth realm
        if (!paramRealm) {
            this.realm = authRealm;
        } else {
            this.realm = paramRealm;
        }

        // Navigate to the given auth realm if no param realm is provided
        if (!paramRealm) {
            console.log(`No realm provided, redirecting to ${authRealm}`);
            return commands.redirect(authRealm);
        }

        // Initialise the OpenRemote manager rest api
        manager.rest.initialise(ML_OR_URL + '/api/' + authRealm);

        setRealmTheme(this.realm);
    }

    // Render the breadcrumb nav and slot
    render() {
        return html`
            <breadcrumb-nav realm=${this.realm}></breadcrumb-nav>
            <slot></slot>
        `;
    }
}
