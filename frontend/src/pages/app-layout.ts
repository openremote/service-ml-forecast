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
import { html, LitElement } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { setRealmTheme } from '../common/theme';
import { manager } from '@openremote/core';
import { ML_OR_URL } from '../common/constants';

export const realmContext = createContext<string>(Symbol('realm'));

@customElement('app-layout')
export class AppLayout extends LitElement {
    // Provide the realm to all child elements
    @provide({ context: realmContext })
    @state()
    realm = '';

    // Vaadin router lifecycle hook -- runs exactly once since this is the parent route
    async onBeforeEnter(location: RouterLocation, commands: PreventAndRedirectCommands) {
        const authRealm = manager.getRealm() ?? 'master';
        const paramRealm = location.params.realm as string;

        // Redirect to auth realm, if no param realm is provided
        if (!paramRealm) {
            console.log(`No realm provided, redirecting to ${authRealm}`);
            return commands.redirect(authRealm);
        }

        this.realm = paramRealm;

        // Initialize the OpenRemote manager rest api using the authenticated realm
        manager.rest.initialise(`${ML_OR_URL}/api/${authRealm}`);

        // Set the service UI theme based on the given realm
        setRealmTheme(this.realm);
    }

    render() {
        return html`
            <breadcrumb-nav realm=${this.realm}></breadcrumb-nav>
            <slot></slot>
        `;
    }
}
