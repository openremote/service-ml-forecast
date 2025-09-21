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

import { TemplateResult } from 'lit';
import { ModelTypeEnum, ModelConfig } from '../../services/models';
import { OrInputChangedEvent } from '@openremote/or-mwc-components/or-mwc-input';
import { ProphetConfig } from './prophet-config';
import { XGBoostConfig } from './xgboost-config';

/**
 * Interface for model type configuration.
 * Each model type should implement this interface to define its behavior.
 */
export interface ModelTypeConfig {
    /** Human-readable label for the model type */
    label: string;
    
    /** Default configuration values for this model type */
    defaultConfig: Partial<ModelConfig>;
    
    /** Generate the parameters template for this model type */
    getParametersTemplate: (
        config: ModelConfig, 
        handleInput: (ev: OrInputChangedEvent) => void
    ) => TemplateResult;
    
    /** Generate the covariates template for this model type */
    getCovariatesTemplate: (
        config: ModelConfig,
        context: {
            assetSelectList: Map<string, string>;
            attributeSelectList: Map<string, Map<string, string>>;
            searchAssets: (search?: string) => Promise<[any, string][]>;
            requestUpdate: () => void;
            handleInput: (ev: OrInputChangedEvent, index: number, type?: string) => void;
        }
    ) => TemplateResult;
    
    /** Validate the configuration for this model type */
    validateConfig: (config: ModelConfig) => boolean;
}

/**
 * Registry for managing model type configurations.
 * This allows for dynamic registration and retrieval of model types.
 */
export class ModelTypeRegistry {
    private static configs = new Map<ModelTypeEnum, ModelTypeConfig>();

    /**
     * Register a model type configuration
     */
    static register(type: ModelTypeEnum, config: ModelTypeConfig) {
        this.configs.set(type, config);
    }

    /**
     * Get a model type configuration
     */
    static get(type: ModelTypeEnum): ModelTypeConfig | undefined {
        return this.configs.get(type);
    }

    /**
     * Get all registered model type configurations
     */
    static getAll(): Array<[ModelTypeEnum, ModelTypeConfig]> {
        return Array.from(this.configs.entries());
    }

    /**
     * Get select options for dropdown menus
     */
    static getSelectOptions(): Array<[string, string]> {
        return Array.from(this.configs.entries()).map(([type, config]) => [type, config.label]);
    }

    /**
     * Check if a model type is registered
     */
    static has(type: ModelTypeEnum): boolean {
        return this.configs.has(type);
    }

    /**
     * Clear all registered configurations (mainly for testing)
     */
    static clear() {
        this.configs.clear();
    }

    /**
     * Register all available model configurations.
     * This function should be called once during application initialization
     * to make all model types available to the editor.
     */
    static registerAllConfigs(): void {
        this.register(ModelTypeEnum.PROPHET, ProphetConfig);
        this.register(ModelTypeEnum.XGBOOST, XGBoostConfig);
    }
}
