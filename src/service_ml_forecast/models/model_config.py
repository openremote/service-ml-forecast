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

from enum import Enum
from typing import Annotated, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from service_ml_forecast.models.model_type import ModelTypeEnum


class AssetAttributeFeature(BaseModel):
    asset_id: str = Field(description="Asset ID.")
    attribute_name: str = Field(
        description="Name of the attribute of the asset. This attribute requires historical data.",
    )
    cutoff_timestamp: int = Field(
        description="Timestamp in milliseconds since epoch, all data after this timestamp will be used.",
    )


class BaseModelConfig(BaseModel):
    """Base configuration for all ML models."""

    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="ID of the model configuration. If not provided, a random uuid will be generated.",
    )
    realm: str = Field(description="Realm of where the assets and their datapoints are available.")
    name: str = Field(description="Friendly name for the model configuration.")
    type: ModelTypeEnum = Field(description="Which machine learning model to use.")
    target: AssetAttributeFeature = Field(
        description="Asset attribute datapoint to predict. This datapoint must have historical data available.",
    )
    regressors: list[AssetAttributeFeature] | None = Field(
        default=None,
        description="List of model input asset attributes that will be used as regressors. "
        "They must have historical data and predicted values available for the configured forecast period.",
    )
    forecast_interval: str = Field(description="Forecast generation interval. Expects ISO 8601 duration strings.")
    training_interval: str = Field(description="Model training interval. Expects ISO 8601 duration strings.")
    forecast_periods: int = Field(description="Number of periods to forecast.")
    forecast_frequency: str = Field(
        description="The frequency of each forecasted datapoint. Expects a pandas offset string. E.g. '30min' or '1h'. "
        "Generated forecast datapoints are rounded to the nearest frequency. Example: 15:30 -> 16:00 -> 16:30 etc.",
    )


class ProphetSeasonalityModeEnum(str, Enum):
    ADDITIVE = "additive"
    MULTIPLICATIVE = "multiplicative"


class ProphetModelConfig(BaseModelConfig):
    """Prophet specific configuration."""

    type: Literal[ModelTypeEnum.PROPHET] = ModelTypeEnum.PROPHET
    yearly_seasonality: bool = Field(
        default=True,
        description="Include yearly seasonality in the model.",
    )
    weekly_seasonality: bool = Field(
        default=True,
        description="Include weekly seasonality in the model.",
    )
    daily_seasonality: bool = Field(
        default=True,
        description="Include daily seasonality in the model.",
    )
    seasonality_mode: ProphetSeasonalityModeEnum = Field(
        default=ProphetSeasonalityModeEnum.ADDITIVE,
        description="Seasonality mode of the model. Additive or multiplicative.",
    )
    changepoint_range: float = Field(
        default=0.8,
        description="Proportion of historical data used for detecting changepoints. "
        "A higher value (e.g., 0.9-1.0) makes the model more responsive to recent trends.",
    )

    changepoint_prior_scale: float = Field(
        default=0.05,
        description="Controls trend flexibility at changepoints. "
        "Lower values (e.g., 0.01) result in smoother trends, "
        "while higher values (e.g., 0.5) allow more abrupt changes.",
    )


ModelConfig = Annotated[
    ProphetModelConfig,
    Field(discriminator="type"),
]
