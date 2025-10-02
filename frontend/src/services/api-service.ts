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

import { ModelConfig } from './models';
import { ML_SERVICE_URL } from '../common/constants';
import { manager } from '@openremote/core';

/**
 * Build the service url with the api path
 * @param realm The realm for the API
 * @returns The service url with the api path
 */
function getServiceBaseUrl(realm: string): string {
    return ML_SERVICE_URL + '/api/' + realm;
}

/**
 * Build the headers for the API request
 * @returns The headers for the API request
 */
function buildHeaders(): Headers {
    return new Headers({
        'Content-Type': 'application/json',
        Authorization: `Bearer ${manager.getKeycloakToken()}`
    });
}

export const APIService = {
    /**
     * Get all model configs for the current realm
     * @returns The list of model configs
     */
    async getModelConfigs(realm: string): Promise<ModelConfig[]> {
        const response = await fetch(getServiceBaseUrl(realm) + '/configs', {
            method: 'GET',
            headers: buildHeaders()
        });
        if (!response.ok) {
            throw new Error(`Failed to get model configs: ${response.statusText}`);
        }
        return response.json();
    },

    /**
     * Get a model config by id
     * @param realm The realm of the model config
     * @param id The id of the model config
     * @returns The model config
     */
    async getModelConfig(realm: string, id: string): Promise<ModelConfig> {
        const response = await fetch(getServiceBaseUrl(realm) + '/configs/' + id, {
            method: 'GET',
            headers: buildHeaders()
        });
        if (!response.ok) {
            throw new Error(`Failed to get model config ${id}: ${response.statusText}`);
        }
        return response.json();
    },

    /**
     * Delete a model config by id
     * @param realm The realm of the model config
     * @param id The id of the model config
     */
    async deleteModelConfig(realm: string, id: string): Promise<void> {
        const response = await fetch(getServiceBaseUrl(realm) + '/configs/' + id, {
            method: 'DELETE',
            headers: buildHeaders()
        });
        if (!response.ok) {
            throw new Error(`Failed to delete model config ${id}: ${response.statusText}`);
        }
    },

    /**
     * Update a model config
     * @param realm The realm of the model config
     * @param id The id of the model config
     * @param modelConfig The model config to update
     * @returns The updated model config
     */
    async updateModelConfig(realm: string, id: string, modelConfig: ModelConfig): Promise<ModelConfig> {
        const response = await fetch(getServiceBaseUrl(realm) + '/configs/' + id, {
            method: 'PUT',
            body: JSON.stringify(modelConfig),
            headers: buildHeaders()
        });
        if (!response.ok) {
            throw new Error(`Failed to update model config: ${response.statusText}`);
        }
        return response.json();
    },

    /**
     * Create a model config
     * @param realm The realm of the model config
     * @param modelConfig The model config to create
     * @returns The created model config
     */
    async createModelConfig(realm: string, modelConfig: ModelConfig): Promise<ModelConfig> {
        const response = await fetch(getServiceBaseUrl(realm) + '/configs', {
            method: 'POST',
            body: JSON.stringify(modelConfig),
            headers: buildHeaders()
        });
        if (!response.ok) {
            throw new Error(`Failed to create model config: ${response.statusText}`);
        }
        return response.json();
    }
};
