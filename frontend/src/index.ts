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

import { Router } from '@vaadin/router'
import './pages/pages-config-list'
import './pages/pages-config-editor'
import './pages/pages-not-found'
import './pages/app-layout'
import { setupORIcons, getRootPath } from './util'

async function init() {
    const outlet = document.querySelector('#outlet') as HTMLElement

    // Setup OR icons
    setupORIcons()

    // Setup the router -- Vaadin expects a trailing slash in the baseUrl
    const router = new Router(outlet, { baseUrl: getRootPath() + '/' })

    initRouter(router)
}

function initRouter(router: Router) {
    // Setup the routes
    const routes = [
        {
            path: '',
            component: 'app-layout',
            children: [
                {
                    path: `/:realm`,
                    redirect: `/:realm/configs`
                },
                {
                    path: `/:realm/configs`,
                    component: 'page-config-list',
                    title: 'Configs'
                },
                {
                    path: `/:realm/configs/new`,
                    component: 'page-config-editor',
                    title: 'New Config'
                },
                {
                    path: `/:realm/configs/:id`,
                    component: 'page-config-editor',
                    title: 'Edit Config'
                },
                {
                    path: '(.*)',
                    component: 'page-not-found'
                }
            ]
        }
    ]

    // Set the routes
    router.setRoutes(routes)
}

// Entry point
await init()
