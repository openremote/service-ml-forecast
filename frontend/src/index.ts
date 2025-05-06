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

import { AuthService } from './services/auth-service'
import { html, render } from 'lit'
import { setupORIcons } from './common/theme'
import { setupRouter } from './router'
import { APP_OUTLET } from './common/constants'
import { isEmbedded, setupConsoleLogging, getRealmParam } from './common/util'

// Override default log statements with service prefix
setupConsoleLogging()

async function init() {
    console.log('Context:', isEmbedded() ? 'iframe embedded' : 'browser standalone')

    try {
        render(html`<loading-spinner></loading-spinner>`, APP_OUTLET)
        await initAuthService()
    } catch (error) {
        console.error('Failed to initialize auth service:', error)
    } finally {
        render(null, APP_OUTLET)
    }

    // Setup OR icons
    setupORIcons()

    // Setup the router
    setupRouter()
}

async function initAuthService() {
    // Initialize the auth service - This will trigger a login if required, prefers SSO if available
    const authenticated = await AuthService.init(getRealmParam() ?? 'master')
    if (!authenticated) {
        AuthService.login()
        return
    }
}

// Entry point
await init()
