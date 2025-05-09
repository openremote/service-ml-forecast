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

/**
 * Get the root path of the application
 * @returns The full root path of the application
 * @remarks This is a workaround to have consistent full root path, rather than relative via the ENV variable.
 * @remarks Neglible performance impact, sub millisecond lookup
 */
export function getRootPath() {
    const scriptElement = document.querySelector('script[src*="bundle"]');

    if (scriptElement && scriptElement.getAttribute('src')) {
        const scriptPath = new URL(scriptElement.getAttribute('src')!, window.location.href).pathname;
        // Positive lookahead to match everything up to bundle.js
        const match = scriptPath.match(/(.*?)(?=bundle)/);
        return match ? (match[1].endsWith('/') ? match[1].slice(0, -1) : match[1]) : '';
    }
    return '';
}
