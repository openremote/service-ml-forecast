import { getRealm } from "../util";
import { Asset, ModelConfig, RealmConfig } from "./models";

export class ApiService {

    // TODO: Make this configurable via environment variable
    private readonly baseUrl: string = "http://localhost:8000"

    async getModelConfigs() : Promise<ModelConfig[]> {
        const realm = getRealm(window.location.pathname);
        const response = await fetch(`${this.baseUrl}/model/config/` + (realm ? `?realm=${realm}` : ''), {
            method: "GET",
        });
        return response.json();
    }

    async getAssets(ids: string[]) : Promise<Asset[]> {
        const realm = getRealm(window.location.pathname);
        const response = await fetch(`${this.baseUrl}/openremote/assets/ids` + (realm ? `?realm=${realm}&ids=${ids.join(',')}` : ''), {
            method: "GET",
        });
        return response.json();
    }

    async getModelConfig(id: string) : Promise<ModelConfig> {
        const response = await fetch(`${this.baseUrl}/model/config/${id}`, {
            method: "GET",
        });
        return response.json();
    }

    async deleteModelConfig(id: string) : Promise<void> {
        const response = await fetch(`${this.baseUrl}/model/config/${id}`, {
            method: "DELETE",
        });
        return response.json();
    }

    async updateModelConfig(modelConfig: ModelConfig) : Promise<void> {
        const response = await fetch(`${this.baseUrl}/model/config/${modelConfig.id}`, {
            method: "PUT",
            body: JSON.stringify(modelConfig),
        });
        return response.json();
    }

    async createModelConfig(modelConfig: ModelConfig) : Promise<void> {
        const response = await fetch(`${this.baseUrl}/model/config`, {
            method: "POST",
            body: JSON.stringify(modelConfig),
        });
        return response.json();
    }

    async getRealmConfig(realm: string) : Promise<RealmConfig> {
        const response = await fetch(`${this.baseUrl}/openremote/realm/config/${realm}`, {
            method: "GET",
        });
        return response.json();
    }
    
    
}
