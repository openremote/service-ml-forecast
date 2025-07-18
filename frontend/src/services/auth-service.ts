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

import Keycloak from 'keycloak-js';
import { IS_EMBEDDED } from '../common/constants';
import { manager } from '@openremote/core';
import { AxiosRequestConfig } from 'axios';

const keycloakUrl: string = (process.env.ML_OR_KEYCLOAK_URL || '').replace(/\/$/, '');

type AuthChangeListener = () => void;

class AuthServiceClass {
    token: string | undefined = '';
    authenticated: boolean = false;
    user: string | undefined = '';
    realm: string = '';
    initializing: boolean = false;
    initPromise: Promise<boolean> | null = null;
    keycloak: Keycloak | undefined;

    private listeners: AuthChangeListener[] = [];
    private tokenRefreshInterval: NodeJS.Timeout | null = null;

    /**
     * Initialize the Keycloak instance
     * @param realm The realm to initialize the Keycloak instance for
     * @param force Whether to force the initialization
     * @returns True if the initialization was successful, false otherwise
     */
    async init(realm: string, force = false): Promise<boolean> {
        if (this.initializing && !force) {
            console.warn('Already initializing', realm);
            return this.initPromise!;
        }
        if (this.keycloak && this.realm === realm && !force) {
            console.warn('Already initialized', realm);
            return this.authenticated;
        }

        this.initializing = true;
        this.realm = realm;
        const keycloakInstance = new Keycloak({
            url: keycloakUrl,
            realm: realm,
            clientId: 'openremote'
        });

        this.initPromise = keycloakInstance
            .init({
                onLoad: 'check-sso',
                checkLoginIframe: false,
                silentCheckSsoFallback: true
            })
            .then((auth: boolean) => {
                this.keycloak = keycloakInstance;
                this.authenticated = auth;
                this.token = keycloakInstance.token;
                this.user = keycloakInstance.tokenParsed?.preferred_username;
                this.initializing = false;
                this.notify();

                if (!IS_EMBEDDED) {
                    this.startUpdateTokenInterval();
                }

                // Add the interceptor for interacting with the OpenRemote manager rest api
                manager.rest.addRequestInterceptor((config: AxiosRequestConfig) => {
                    if (!config!.headers!.Authorization) {
                        const authHeader = `Bearer ${this.token}`;

                        if (authHeader) {
                            config!.headers!.Authorization = authHeader;
                        }
                    }

                    return config;
                });

                return auth;
            })
            .catch((error: any) => {
                console.error(`Keycloak initialization failed for realm ${realm}:`, error);
                this.keycloak = undefined;
                this.authenticated = false;
                this.token = undefined;
                this.user = undefined;
                this.initializing = false;
                this.notify();
                return false;
            });

        return this.initPromise!;
    }

    /**
     * Login to the Keycloak instance
     */
    async login() {
        await this.keycloak?.login();
    }

    /**
     * Logout from the Keycloak instance
     */
    async logout() {
        await this.keycloak?.logout();
        this.stopUpdateTokenInterval();
    }

    private startUpdateTokenInterval() {
        if (this.tokenRefreshInterval) {
            clearInterval(this.tokenRefreshInterval);
        }
        this.tokenRefreshInterval = setInterval(() => this.updateToken(), 5000);
    }

    private stopUpdateTokenInterval() {
        if (this.tokenRefreshInterval) {
            clearInterval(this.tokenRefreshInterval);
            this.tokenRefreshInterval = null;
        }
    }

    /**
     * Update the token, if it expires in the next 20 seconds
     * @returns True if the token was refreshed, false otherwise
     */
    async updateToken(): Promise<boolean> {
        if (!this.keycloak) {
            return false;
        }
        try {
            const refreshed = await this.keycloak.updateToken(20);
            if (refreshed) {
                this.token = this.keycloak.token;
                this.notify();
            }
            return refreshed;
        } catch (error) {
            console.error('Token refresh failed.', error);
            return false;
        }
    }

    /**
     * Subscribe to authentication changes
     * @param listener The listener to subscribe to
     * @returns A function to unsubscribe from the listener
     */
    subscribe(listener: AuthChangeListener): () => void {
        this.listeners.push(listener);
        return () => {
            this.listeners = this.listeners.filter((l) => l !== listener);
        };
    }

    private notify(): void {
        this.listeners.forEach((listener) => listener());
    }
}

/**
 * Singleton for handling authentication
 */
export const AuthService = new AuthServiceClass();
