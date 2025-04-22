import { CustomAsset, ModelConfig, RealmConfig } from './models'
import { AuthService } from './auth-service'
// Use env variable, else fallback to relative URL (e.g. front-end on the same host as the ML service)
const baseUrl: string = (process.env.ML_SERVICE_URL || '').replace(/\/$/, '')

export class APIServiceClass {
    /**
     * Build the headers for the API request
     * @returns The headers
     */
    private buildHeaders(): Record<string, string> {
        AuthService.updateToken() // Ensure token is refreshed
        const token = AuthService.token
        if (!token) {
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
        const response = await fetch(`${baseUrl}/api/model/configs` + (realm ? `?realm=${realm}` : ''), {
            method: 'GET',
            headers: this.buildHeaders()
        })
        if (!response.ok) {
            throw new Error(`Failed to get model configs: ${response.statusText}`)
        }
        return response.json()
    }

    /**
     * Get all assets for the current realm with attributes that store datapoints
     * @param realm The realm name
     * @returns The list of assets
     */
    async getAssets(realm: string): Promise<CustomAsset[]> {
        const response = await fetch(`${baseUrl}/api/openremote/assets` + (realm ? `?realm=${realm}` : ''), {
            method: 'GET',
            headers: this.buildHeaders()
        })
        if (!response.ok) {
            throw new Error(`Failed to get assets: ${response.statusText}`)
        }
        return response.json()
    }

    /**
     * Get assets by ids for the current realm
     * @param ids The list of asset ids
     * @param realm The realm name
     * @returns The list of assets
     */
    async getAssetsByIds(ids: string[], realm: string): Promise<CustomAsset[]> {
        const response = await fetch(`${baseUrl}/api/openremote/assets/ids?realm=${realm}&ids=${ids.join(',')}`, {
            method: 'GET',
            headers: this.buildHeaders()
        })
        if (!response.ok) {
            throw new Error(`Failed to get assets: ${response.statusText}`)
        }
        return response.json()
    }

    /**
     * Get a model config by id
     * @param id The id of the model config
     * @returns The model config
     */
    async getModelConfig(id: string): Promise<ModelConfig> {
        const response = await fetch(`${baseUrl}/api/model/configs/${id}`, {
            method: 'GET',
            headers: this.buildHeaders()
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
    async deleteModelConfig(id: string): Promise<void> {
        const response = await fetch(`${baseUrl}/api/model/configs/${id}`, {
            method: 'DELETE',
            headers: this.buildHeaders()
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
    async updateModelConfig(modelConfig: ModelConfig): Promise<ModelConfig> {
        const response = await fetch(`${baseUrl}/api/model/configs/${modelConfig.id}`, {
            method: 'PUT',
            body: JSON.stringify(modelConfig),
            headers: {
                'Content-Type': 'application/json',
                ...this.buildHeaders()
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
    async createModelConfig(modelConfig: ModelConfig): Promise<ModelConfig> {
        const response = await fetch(`${baseUrl}/api/model/configs`, {
            method: 'POST',
            body: JSON.stringify(modelConfig),
            headers: {
                'Content-Type': 'application/json',
                ...this.buildHeaders()
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
    async getRealmConfig(realm: string): Promise<RealmConfig> {
        const response = await fetch(`${baseUrl}/api/openremote/realm/config/${realm}`, {
            method: 'GET',
            headers: this.buildHeaders()
        })

        if (!response.ok) {
            throw new Error(`Failed to get realm config: ${response.statusText}`)
        }
        return response.json()
    }
}

/**
 * Singleton for interacting with the ML service API
 */
export const APIService = new APIServiceClass()
