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

// Component Imports
import '@openremote/or-mwc-components/or-mwc-input';
import '@openremote/or-panel';
import '@openremote/or-icon';
import './components/custom-duration-input';
import './components/configs-table';
import './components/loading-spinner';
import './components/breadcrumb-nav';

import { setupORIcons } from './common/theme';
import { setupRouter } from './router';

function init() {
    // Setup OR icons
    setupORIcons();

    // Setup the router
    setupRouter();
}

// Entry point
init();
