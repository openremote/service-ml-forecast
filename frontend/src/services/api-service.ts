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

import { CustomAsset, ModelConfig, RealmConfig } from './models'
import { AuthService } from './auth-service'
// Use env variable, else fallback to relative URL (e.g. front-end on the same host as the ML service)
const baseUrl: string = (process.env.ML_SERVICE_URL || '').replace(/\/$/, '')

export class APIServiceClass {
    /**
     * Build the headers for the API request
     * @returns The headers
     */
    private async buildHeaders(): Promise<Record<string, string>> {
        await AuthService.updateToken()
        const token = AuthService.token
        if (!token) {
            console.error('Unable to build authorization headers: no token')
            return {}
        }
        return {
            Authorization: `Bearer ${token}`
        }
    }

    /**
     * Get all model configs for the current realm
     * @param realm The realm name
     * @returns The list of model configs
     */
    async getModelConfigs(realm: string): Promise<ModelConfig[]> {
        const response = await fetch(`${baseUrl}/api/${realm}/configs`, {
            method: 'GET',
            headers: await this.buildHeaders()
        })
        if (!response.ok) {
            throw new Error(`Failed to get model configs: ${response.statusText}`)
        }
        return response.json()
    }

    /**
     * Get a model config by id
     * @param id The id of the model config
     * @returns The model config
     */
    async getModelConfig(realm: string, id: string): Promise<ModelConfig> {
        const response = await fetch(`${baseUrl}/api/${realm}/configs/${id}`, {
            method: 'GET',
            headers: await this.buildHeaders()
        })
        if (!response.ok) {
            throw new Error(`Failed to get model config ${id}: ${response.statusText}`)
        }
        return response.json()
    }

    /**
     * Delete a model config by id
     * @param id The id of the model config
     */
    async deleteModelConfig(realm: string, id: string): Promise<void> {
        const response = await fetch(`${baseUrl}/api/${realm}/configs/${id}`, {
            method: 'DELETE',
            headers: await this.buildHeaders()
        })
        if (!response.ok) {
            throw new Error(`Failed to delete model config ${id}: ${response.statusText}`)
        }
    }

    /**
     * Update a model config
     * @param modelConfig The model config to update
     * @returns The updated model config
     */
    async updateModelConfig(realm: string, id: string, modelConfig: ModelConfig): Promise<ModelConfig> {
        const response = await fetch(`${baseUrl}/api/${realm}/configs/${id}`, {
            method: 'PUT',
            body: JSON.stringify(modelConfig),
            headers: {
                'Content-Type': 'application/json',
                ...(await this.buildHeaders())
            }
        })
        if (!response.ok) {
            throw new Error(`Failed to update model config: ${response.statusText}`)
        }
        return response.json()
    }

    /**
     * Create a model config
     * @param modelConfig The model config to create
     * @returns The created model config
     */
    async createModelConfig(realm: string, modelConfig: ModelConfig): Promise<ModelConfig> {
        const response = await fetch(`${baseUrl}/api/${realm}/configs`, {
            method: 'POST',
            body: JSON.stringify(modelConfig),
            headers: {
                'Content-Type': 'application/json',
                ...(await this.buildHeaders())
            }
        })
        if (!response.ok) {
            throw new Error(`Failed to create model config: ${response.statusText}`)
        }
        return response.json()
    }

    /**
     * Get the realm config for the current realm (for styling purposes)
     * @param realm The realm name
     * @returns The realm config
     */
    async getOpenRemoteRealmConfig(realm: string): Promise<RealmConfig> {
        const response = await fetch(`${baseUrl}/openremote/${realm}/realm/config`, {
            method: 'GET',
            headers: await this.buildHeaders()
        })

        if (!response.ok) {
            throw new Error(`Failed to get realm config: ${response.statusText}`)
        }
        return response.json()
    }

    /**
     * Get all assets for the current realm with attributesthat store datapoints
     * @returns The list of assets
     */
    async getOpenRemoteAssets(realm: string): Promise<CustomAsset[]> {
        const response = await fetch(`${baseUrl}/openremote/${realm}/assets`, {
            method: 'GET',
            headers: await this.buildHeaders()
        })
        if (!response.ok) {
            throw new Error(`Failed to get assets: ${response.statusText}`)
        }
        return response.json()
    }

    /**
     * Get assets by ids for the current realm
     * @param ids The list of asset ids
     * @returns The list of assets
     */
    async getOpenRemoteAssetsById(realm: string, ids: string[]): Promise<CustomAsset[]> {
        const response = await fetch(`${baseUrl}/openremote/${realm}/assets/ids?ids=${ids.join(',')}`, {
            method: 'GET',
            headers: await this.buildHeaders()
        })
        if (!response.ok) {
            throw new Error(`Failed to get assets: ${response.statusText}`)
        }
        return response.json()
    }
}

/**
 * Singleton for interacting with the ML service API
 */
export const APIService = new APIServiceClass()
