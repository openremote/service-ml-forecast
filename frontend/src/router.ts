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

// Page Imports
import './pages/pages-config-list';
import './pages/pages-config-editor';
import './pages/pages-not-found';
import './pages/app-layout';

import { Router } from '@vaadin/router';
import { getRootPath } from './common/util';
import { APP_OUTLET } from './common/constants';

export interface BreadcrumbMeta {
    label?: string;
    icon?: string;
    hideInEmbedded?: boolean;
}

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
                title: 'Configs',
                breadcrumb: { label: 'Configs', hideInEmbedded: false } as BreadcrumbMeta
            },
            {
                path: `/:realm/configs/new`,
                component: 'page-config-editor',
                title: 'New Config',
                breadcrumb: { label: 'New Config', hideInEmbedded: false } as BreadcrumbMeta
            },
            {
                path: `/:realm/configs/:id`,
                component: 'page-config-editor',
                title: 'Edit Config',
                breadcrumb: { label: ':id', hideInEmbedded: false } as BreadcrumbMeta
            },
            {
                path: '(.*)',
                component: 'page-not-found'
            }
        ]
    }
];

export function setupRouter() {
    // Setup the router -- Vaadin expects a trailing slash in the baseUrl
    const router = new Router(APP_OUTLET, { baseUrl: getRootPath() + '/' });
    router.setRoutes(routes);
}
