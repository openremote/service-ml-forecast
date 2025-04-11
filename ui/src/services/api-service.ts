import { getRealm } from "../util";
import { Asset, ModelConfig, RealmConfig } from "./models";

export class ApiService {

    // TODO: Make this configurable via environment variable
    private readonly baseUrl: string = "http://localhost:8000"

    async getModelConfigs() : Promise<ModelConfig[]> {
        const realm = getRealm();
        const response = await fetch(`${this.baseUrl}/model/config/` + (realm ? `?realm=${realm}` : ''), {
            method: "GET",
        });
        if (!response.ok) {
            throw new Error(`Failed to get model configs: ${response.statusText}`);
        }
        return response.json();
    }

    async getAssets(ids: string[]) : Promise<Asset[]> {
        const realm = getRealm();
        const response = await fetch(`${this.baseUrl}/openremote/assets/ids` + (realm ? `?realm=${realm}&ids=${ids.join(',')}` : ''), {
            method: "GET",
        });
        if (!response.ok) {
            throw new Error(`Failed to get assets: ${response.statusText}`);
        }
        return response.json();
    }

    async getModelConfig(id: string) : Promise<ModelConfig> {
        const response = await fetch(`${this.baseUrl}/model/config/${id}`, {
            method: "GET",
        });
        if (!response.ok) {
            throw new Error(`Failed to get model config ${id}: ${response.statusText}`);
        }
        return response.json();
    }

    async deleteModelConfig(id: string) : Promise<void> {
        const response = await fetch(`${this.baseUrl}/model/config/${id}`, {
            method: "DELETE",
        });
        if (!response.ok) {
            throw new Error(`Failed to delete model config ${id}: ${response.statusText}`);
        }
    }

    async updateModelConfig(modelConfig: ModelConfig) : Promise<ModelConfig> {
        const response = await fetch(`${this.baseUrl}/model/config`, {
            method: "PUT",
            body: JSON.stringify(modelConfig),
            headers: {
                "Content-Type": "application/json",
            },
        });
        if (!response.ok) {
            throw new Error(`Failed to update model config: ${response.statusText}`);
        }
        return response.json();
    }

    async createModelConfig(modelConfig: ModelConfig) : Promise<ModelConfig> {
        const response = await fetch(`${this.baseUrl}/model/config`, {
            method: "POST",
            body: JSON.stringify(modelConfig),
            headers: {
                "Content-Type": "application/json",
            },
        });
        if (!response.ok) {
            throw new Error(`Failed to create model config: ${response.statusText}`);
        }
        return response.json();
    }

    async getRealmConfig(realm: string) : Promise<RealmConfig> {
        const response = await fetch(`${this.baseUrl}/openremote/realm/config/${realm}`, {
            method: "GET",
        });
        if (!response.ok) {
            throw new Error(`Failed to get realm config ${realm}: ${response.statusText}`);
        }
        return response.json();
    }
    
    
}
