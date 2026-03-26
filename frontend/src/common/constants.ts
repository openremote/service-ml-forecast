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

export const APP_OUTLET = document.querySelector('#outlet') as HTMLElement;
type RuntimeConfig = {
    ML_SERVICE_URL?: string;
    ML_OR_URL?: string;
    ML_OR_KEYCLOAK_URL?: string;
};

declare global {
    interface Window {
        APP_CONFIG?: RuntimeConfig;
    }
}

const runtimeConfig = window.APP_CONFIG ?? {};
const bundledEnv = typeof process !== 'undefined' ? process.env : undefined;

export const IS_DEVELOPMENT = bundledEnv?.NODE_ENV === 'development';

export const ML_SERVICE_URL = (runtimeConfig.ML_SERVICE_URL ?? bundledEnv?.ML_SERVICE_URL ?? '').replace(/\/$/, '');

export const ML_OR_URL = runtimeConfig.ML_OR_URL ?? bundledEnv?.ML_OR_URL ?? '';
export const ML_OR_KEYCLOAK_URL = runtimeConfig.ML_OR_KEYCLOAK_URL ?? bundledEnv?.ML_OR_KEYCLOAK_URL ?? '';

// Returns true if the app is embedded in an iframe
export const IS_EMBEDDED = window.top !== window.self;
