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
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from uuid import uuid4

from pydantic import BaseModel, Field

from service_ml_forecast.models.ml_model_type import MLModelTypeEnum


class AssetAttributeFeature(BaseModel):
    asset_id: str = Field(description="The id of the asset. This is the id of the asset in the OpenRemote API.")
    attribute_name: str = Field(
        description="The name of the attribute of the asset from OpenRemote. This attribute requires historical data."
    )
    cutoff_timestamp: int = Field(
        description="The timestamp to use for training, all data after this timestamp will be used."
    )


class MLModelConfig(BaseModel):
    """Base configuration for all ML models."""

    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="ID of the model configuration. If not provided, a random uuid will be generated.",
    )
    realm: str = Field(description="The realm of where the assets and their datapoints are available.")
    name: str = Field(description="A friendly name for the model configuration.")
    type: MLModelTypeEnum = Field(description="Which machine learning model to use.")
    target: AssetAttributeFeature = Field(
        description="The asset attribute datapoint to predict. This datapoint must have historical data available."
    )
    regressors: list[AssetAttributeFeature] | None = Field(
        default=None,
        description="List of model input asset attributes that will be used as regressors. "
        "They must have historical data and predicted values available for the configured forecast period.",
    )
    forecast_interval: str = Field(description="Forecast generation interval. Expects ISO 8601 duration strings.")
    training_interval: str = Field(description="Model training interval. Expects ISO 8601 duration strings.")
    forecast_periods: int = Field(description="The number of periods to forecast.")
    forecast_frequency: str = Field(
        description="The frequency of each forecasted datapoint. Expects a pandas offset string. E.g. '30min' or '1h'."
    )


class ProphetModelConfig(MLModelConfig):
    """Prophet specific configuration."""

    type: MLModelTypeEnum = MLModelTypeEnum.PROPHET
    yearly_seasonality: bool = Field(
        default=True,
        description="Whether to include yearly seasonality in the model.",
    )
    weekly_seasonality: bool = Field(
        default=True,
        description="Whether to include weekly seasonality in the model.",
    )
    daily_seasonality: bool = Field(
        default=True,
        description="Whether to include daily seasonality in the model.",
    )
