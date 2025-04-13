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

from enum import Enum
from typing import Annotated, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from service_ml_forecast.models.model_type import ModelTypeEnum



class RegressorFeature(BaseModel):
    """Regressor feature with the asset id, attribute name and the cutoff timestamp."""

    asset_id: str = Field(description="ID of the asset from OpenRemote.", min_length=22, max_length=22)
    attribute_name: str = Field(
        description="Name of the attribute of the asset.",
        min_length=3,
    )
    cutoff_timestamp: int = Field(
        description="Timestamp in milliseconds since epoch, all data after this timestamp will be used.",
        gt=0,
    )

    # Used for model training and forecasting -- requiring unique feature name
    def get_feature_name(self) -> str:
        """Get the feature name for the regressor feature."""
        return f"{self.asset_id}.{self.attribute_name}"

class TargetFeature(BaseModel):
    """Target feature with the asset id, attribute name and the cutoff timestamp."""

    asset_id: str = Field(description="ID of the asset from OpenRemote.", min_length=22, max_length=22)
    attribute_name: str = Field(
        description="Name of the attribute of the asset.",
        min_length=3,
    )
    cutoff_timestamp: int = Field(
        description="Timestamp in milliseconds since epoch, all data after this timestamp will be used.",
        gt=0,
    )

class BaseModelConfig(BaseModel):
    """Base configuration for all ML models."""

    id: UUID = Field(
        default_factory=uuid4,
        description="ID of the model configuration. If not provided, a random uuid v4 will be generated.",
    )
    realm: str = Field(description="Realm of where the assets and their datapoints are available.")
    name: str = Field(description="Friendly name for the model configuration.")
    enabled: bool = Field(
        default=True,
        description="Whether the model is enabled and will be scheduled for training and forecasting.",
    )
    type: ModelTypeEnum = Field(description="Which machine learning model to use.")
    target: TargetFeature = Field(
        description="The asset attribute to generate datapoints for. "
        "There must be historical data available for training.",
    )
    regressors: list[RegressorFeature] | None = Field(
        default=None,
        description="List of asset attributes that will be used as regressors. "
        "There must be historical data available for training.",
    )
    forecast_interval: str = Field(description="Forecast generation interval. Expects ISO 8601 duration strings.")
    training_interval: str = Field(description="Model training interval. Expects ISO 8601 duration strings.")
    forecast_periods: int = Field(description="Number of periods to forecast.")
    forecast_frequency: str = Field(
        description="The frequency of each forecasted datapoint. "
        "Expects a pandas frequency string. E.g. '30min' or '1h'. "
        "Generated forecast datapoints are rounded to the nearest frequency. "
        "Example: 15:30 -> 16:00 -> 16:30 etc.",
    )


class ProphetSeasonalityModeEnum(str, Enum):
    """Seasonality modes of the Prophet model."""

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
        ge=0.0,
        le=1.0,
    )
    changepoint_prior_scale: float = Field(
        default=0.05,
        description="Controls trend flexibility at changepoints. "
        "Lower values (e.g., 0.01) result in smoother trends, "
        "while higher values (e.g., 0.5) allow more abrupt changes.",
        ge=0.0,
        le=1.0,
    )


ModelConfig = Annotated[
    ProphetModelConfig,
    Field(discriminator="type"),
]
