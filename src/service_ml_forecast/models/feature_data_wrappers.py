# Copyright 2025, OpenRemote Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from pydantic import BaseModel

from service_ml_forecast.clients.openremote.models import AssetDatapoint


class AssetFeatureDatapoints(BaseModel):
    """Feature with the feature name and the datapoints.

    The feature name is the combined asset id and attribute name e.g. "asset_id.attribute_name".
    """

    feature_name: str
    datapoints: list[AssetDatapoint]


class TrainingDataSet(BaseModel):
    """Training set of the asset target and optional asset regressors.

    The target is required, but the regressors are optional.
    """

    target: AssetFeatureDatapoints
    regressors: list[AssetFeatureDatapoints] | None = None


class ForecastDataSet(BaseModel):
    """Forecast feature set with asset regressors.

    The regressors are required.
    """

    regressors: list[AssetFeatureDatapoints]


class ForecastResult(BaseModel):
    """Forecast result with the asset id, attribute name and the forecasted datapoints.

    The forecast result is a list of AssetDatapoint objects.
    """

    asset_id: str
    attribute_name: str
    datapoints: list[AssetDatapoint]
