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

import { type LightGBMModelConfig, ModelTypeEnum } from '../../services/models';
import type { ModelTypeConfig } from './model-registry';
import { XGBoostConfig } from './xgboost-config';

/** LightGBM shares the Darts tree-model controls and covariate editor. */
export const LightGBMConfig: ModelTypeConfig = {
    ...XGBoostConfig,
    label: 'LightGBM',
    defaultConfig: {
        ...XGBoostConfig.defaultConfig,
        type: ModelTypeEnum.LIGHTGBM
    } as Partial<LightGBMModelConfig>
};
