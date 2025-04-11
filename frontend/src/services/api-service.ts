import { getRealm } from '../util'
import { CustomAsset, ModelConfig, RealmConfig } from './models'

export class ApiService {
    // TODO: Make this configurable via environment variable
    private readonly baseUrl: string = 'http://localhost:8000'

    /**
     * Check if the service is available
     * @returns True if the service is available, false otherwise
     * @remarks This is a temporary endpoint to check if the service is available until we have a proper health check endpoint
     */
    async isServiceAvailable(): Promise<boolean> {
        try {
            const response = await fetch(`${this.baseUrl}/docs`, {
                method: 'GET'
            })
            return response.ok
        } catch (error) {
            console.error('Error checking service availability:', error)
            return false
        }
    }

    /**
     * Get all model configs
     * @returns The list of model configs
     */
    async getModelConfigs(): Promise<ModelConfig[]> {
        const realm = getRealm()
        const response = await fetch(`${this.baseUrl}/model/configs` + (realm ? `?realm=${realm}` : ''), {
            method: 'GET'
        })
        if (!response.ok) {
            throw new Error(`Failed to get model configs: ${response.statusText}`)
        }
        return response.json()
    }

    /**
     * Get all assets
     * @returns The list of assets
     */
    async getAssets(): Promise<CustomAsset[]> {
        const realm = getRealm()
        const response = await fetch(`${this.baseUrl}/openremote/assets` + (realm ? `?realm=${realm}` : ''), {
            method: 'GET'
        })
        if (!response.ok) {
            throw new Error(`Failed to get assets: ${response.statusText}`)
        }
        return response.json()
    }

    /**
     * Get assets by ids
     * @param ids The list of asset ids
     * @returns The list of assets
     */
    async getAssetsByIds(ids: string[]): Promise<CustomAsset[]> {
        const realm = getRealm()
        const response = await fetch(`${this.baseUrl}/openremote/assets/ids?realm=${realm}&ids=${ids.join(',')}`, {
            method: 'GET'
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
        const response = await fetch(`${this.baseUrl}/model/configs/${id}`, {
            method: 'GET'
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
        const response = await fetch(`${this.baseUrl}/model/configs/${id}`, {
            method: 'DELETE'
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
        const response = await fetch(`${this.baseUrl}/model/configs/${modelConfig.id}`, {
            method: 'PUT',
            body: JSON.stringify(modelConfig),
            headers: {
                'Content-Type': 'application/json'
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
        const response = await fetch(`${this.baseUrl}/model/configs`, {
            method: 'POST',
            body: JSON.stringify(modelConfig),
            headers: {
                'Content-Type': 'application/json'
            }
        })
        if (!response.ok) {
            throw new Error(`Failed to create model config: ${response.statusText}`)
        }
        return response.json()
    }

    /**
     * Get the realm config
     * @returns The realm config
     */
    async getRealmConfig(): Promise<RealmConfig> {
        const realm = getRealm()
        const response = await fetch(`${this.baseUrl}/openremote/realm/config/${realm}`, {
            method: 'GET'
        })
        if (!response.ok) {
            throw new Error(`Failed to get realm config: ${response.statusText}`)
        }
        return response.json()
    }
}
