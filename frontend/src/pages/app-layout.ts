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

import { createContext, provide } from '@lit/context'
import { RouterLocation } from '@vaadin/router'
import { html, LitElement } from 'lit'
import { customElement, state } from 'lit/decorators.js'
import { setRealmTheme } from '../common/theme'
import '../components/breadcrumb-nav'

export const realmContext = createContext<string>(Symbol('realm'))

@customElement('app-layout')
export class AppLayout extends LitElement {
    // Provide the realm context to all child elements
    @provide({ context: realmContext })
    @state()
    realm = ''

    // Set the realm when the route changes
    onBeforeEnter(location: RouterLocation) {
        this.realm = location.params.realm as string
        setRealmTheme(this.realm)
    }

    // Render the breadcrumb nav and slot
    render() {
        return html`
            <breadcrumb-nav realm=${this.realm}></breadcrumb-nav>
            <slot></slot>
        `
    }
}
