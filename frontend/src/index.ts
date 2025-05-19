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

import { AuthService } from './services/auth-service';
import { setupORIcons } from './common/theme';
import { setupRouter } from './router';
import { IS_EMBEDDED } from './common/constants';
import { setupConsoleLogging, getRealmParam } from './common/util';

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

async function init() {
    console.info('Context:', IS_EMBEDDED ? 'iframe' : 'standalone');

    await AuthService.init(getRealmParam() ?? 'master');

    // Setup OR icons
    setupORIcons();

    // Setup the router
    setupRouter();
}

init();
