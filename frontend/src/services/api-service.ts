import { CustomAsset, ModelConfig, RealmConfig } from './models'

// Use env variable, else fallback to relative URL (e.g. front-end on the same host as the ML service)
const baseUrl: string = (process.env.ML_SERVICE_URL || '').replace(/\/$/, '')

export const APIService = {
    /**
     * Get all model configs for the current realm
     * @returns The list of model configs
     */
    async getModelConfigs(realm: string): Promise<ModelConfig[]> {
        const response = await fetch(`${baseUrl}/api/${realm}/configs`, {
            method: 'GET'
        })
        if (!response.ok) {
            throw new Error(`Failed to get model configs: ${response.statusText}`)
        }
        return response.json()
    },

    /**
     * Get a model config by id
     * @param id The id of the model config
     * @returns The model config
     */
    async getModelConfig(realm: string, id: string): Promise<ModelConfig> {
        const response = await fetch(`${baseUrl}/api/${realm}/configs/${id}`, {
            method: 'GET'
        })
        if (!response.ok) {
            throw new Error(`Failed to get model config ${id}: ${response.statusText}`)
        }
        return response.json()
    },

    /**
     * Delete a model config by id
     * @param id The id of the model config
     */
    async deleteModelConfig(realm: string, id: string): Promise<void> {
        const response = await fetch(`${baseUrl}/api/${realm}/configs/${id}`, {
            method: 'DELETE'
        })
        if (!response.ok) {
            throw new Error(`Failed to delete model config ${id}: ${response.statusText}`)
        }
    },

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
                'Content-Type': 'application/json'
            }
        })
        if (!response.ok) {
            throw new Error(`Failed to update model config: ${response.statusText}`)
        }
        return response.json()
    },

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
                'Content-Type': 'application/json'
            }
        })
        if (!response.ok) {
            throw new Error(`Failed to create model config: ${response.statusText}`)
        }
        return response.json()
    },

    /**
     * Get the realm config for the current realm (for styling purposes)
     * @returns The realm config
     */
    async getOpenRemoteRealmConfig(realm: string): Promise<RealmConfig> {
        const response = await fetch(`${baseUrl}/openremote/${realm}/realm/config`, {
            method: 'GET'
        })
        if (!response.ok) {
            throw new Error(`Failed to get realm config: ${response.statusText}`)
        }
        return response.json()
    },

    /**
     * Get all assets for the current realm with attributesthat store datapoints
     * @returns The list of assets
     */
    async getOpenRemoteAssets(realm: string): Promise<CustomAsset[]> {
        const response = await fetch(`${baseUrl}/openremote/${realm}/assets`, {
            method: 'GET'
        })
        if (!response.ok) {
            throw new Error(`Failed to get assets: ${response.statusText}`)
        }
        return response.json()
    },

    /**
     * Get assets by ids for the current realm
     * @param ids The list of asset ids
     * @returns The list of assets
     */
    async getOpenRemoteAssetsById(realm: string, ids: string[]): Promise<CustomAsset[]> {
        const response = await fetch(`${baseUrl}/openremote/${realm}/assets/ids?ids=${ids.join(',')}`, {
            method: 'GET'
        })
        if (!response.ok) {
            throw new Error(`Failed to get assets: ${response.statusText}`)
        }
        return response.json()
    }
}
