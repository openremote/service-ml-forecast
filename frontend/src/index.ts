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

import { setupORIcons } from './common/theme';
import { setupRouter } from './router';
import { IS_EMBEDDED, ML_OR_KEYCLOAK_URL, ML_OR_URL } from './common/constants';
import { getRealmSearchParam, setupConsoleLogging } from './common/util';
import { manager } from '@openremote/core';
import { Auth, EventProviderType, ManagerConfig } from '@openremote/model';

// Component Imports
import '@openremote/or-mwc-components/or-mwc-input';
import '@openremote/or-components/or-panel';
import '@openremote/or-icon';
import './components/custom-duration-input';
import './components/configs-table';
import './components/loading-spinner';
import './components/breadcrumb-nav';
import './components/alert-message';

// Override default log statements with service prefix
setupConsoleLogging();

const DEFAULT_MANAGER_CONFIG: ManagerConfig = {
    managerUrl: ML_OR_URL || '',
    keycloakUrl: ML_OR_KEYCLOAK_URL || '',
    auth: Auth.KEYCLOAK,
    autoLogin: true,
    realm: undefined,
    consoleAutoEnable: true,
    loadTranslations: ['or'],
    eventProviderType: EventProviderType.POLLING
};

async function init() {
    console.info('Context:', IS_EMBEDDED ? 'iframe' : 'standalone');

    // get realm search param (?realm=) from url, if not provided, use master for auth
    const realm = getRealmSearchParam() ?? 'master';
    const managerConfig = { ...DEFAULT_MANAGER_CONFIG, realm };

    await setupManager(managerConfig);

    setupORIcons();
    setupRouter();
}

async function setupManager(managerConfig: ManagerConfig) {
    await manager.init(managerConfig);
}

init();
