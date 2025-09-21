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


class AssetDatapointFeature(BaseModel):
    """Base asset feature with the asset id, attribute name and the training data period.

    The asset feature is a covariate that is used for model training and forecasting.
    """

    asset_id: str = Field(description="ID of the asset from OpenRemote.", min_length=22, max_length=22)
    attribute_name: str = Field(
        description="Name of the attribute of the asset.",
        min_length=3,
    )
    training_data_period: str = Field(
        default="P6M",
        description="ISO 8601 duration string, this duration period will be used for retrieving training data. "
        "E.g. 'P6M' for data from the last 6 months.",
    )
    cutoff_timestamp: int | None = Field(
        default=None,
        description="Deprecated, use training_data_period instead.",
        deprecated=True,
    )

    def get_feature_name(self) -> str:
        """Get the feature name for the feature."""
        return f"asset_{self.asset_id}.{self.attribute_name}"


class FutureAssetDatapointFeature(AssetDatapointFeature):
    """Asset feature with the asset id, attribute name and the training data period.

    The asset feature is a covariate that is used for model training and forecasting.
    """

    def get_feature_name(self) -> str:
        """Get the feature name for the feature."""
        return f"future_{self.asset_id}.{self.attribute_name}"


class PastAssetDatapointFeature(AssetDatapointFeature):
    """Asset feature with the asset id, attribute name and the training data period.

    The asset feature is a covariate that is used for model training and forecasting.
    """

    def get_feature_name(self) -> str:
        """Get the feature name for the feature."""
        return f"past_{self.asset_id}.{self.attribute_name}"


class TargetAssetDatapointsFeature(BaseModel):
    """Asset target feature with the asset id, attribute name and the cutoff timestamp.

    The asset target is the asset with an attribute that is being predicted.
    """

    asset_id: str = Field(description="ID of the asset from OpenRemote.", min_length=22, max_length=22)
    attribute_name: str = Field(
        description="Name of the attribute of the asset.",
        min_length=3,
    )
    training_data_period: str = Field(
        default="P6M",
        description="ISO 8601 duration string, this duration period will be used for retrieving training data. "
        "E.g. 'P6M' for data from the last 6 months.",
    )
    cutoff_timestamp: int | None = Field(
        default=None,
        description="Deprecated, use training_data_period instead.",
        deprecated=True,
    )


class BaseModelConfig(BaseModel):
    """Base configuration for all models."""

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
    type: ModelTypeEnum = Field(description="Which model to use.")
    target: TargetAssetDatapointsFeature = Field(
        description="The asset attribute to generate datapoints for. "
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
    regressors: list[FutureAssetDatapointFeature] | None = Field(
        default=None,
        description="List of optional asset attributes that will be used as regressors. "
        "There must be historical data available for training. "
        "There must also be future data available for forecasting.",
    )
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


class XGBoostModelConfig(BaseModelConfig):
    """XGBoost specific configuration."""

    type: Literal[ModelTypeEnum.XGBOOST] = ModelTypeEnum.XGBOOST
    past_covariates: list[PastAssetDatapointFeature] | None = Field(
        default=None,
        description="List of optional asset attributes that will be used as past covariates. "
        "Historical data is required for training. Only historical data is used for forecasting. "
        "Use this when future data cannot be provided.",
    )
    future_covariates: list[FutureAssetDatapointFeature] | None = Field(
        default=None,
        description="List of optional asset attributes that will be used as future covariates. "
        "Both historical and future data must be available for training and forecasting.",
    )
    lags: int | list[int] | None = Field(
        default=24,
        description="Number of lagged observations to use as features. "
        "Can be an integer (number of lags) or list of specific lag values.",
    )
    lags_future_covariates: int | list[int] | None = Field(
        default=None,
        description="Number of lagged future covariates to use as features (non-negative values).",
    )
    lags_past_covariates: int | list[int] | None = Field(
        default=None,
        description="Number of lagged past covariates to use as features (negative values).",
    )
    output_chunk_length: int = Field(
        default=1,
        description="Number of time steps predicted at once by the internal model.",
        ge=1,
    )
    n_estimators: int = Field(
        default=100,
        description="Number of gradient boosted trees.",
        ge=1,
    )
    max_depth: int = Field(
        default=6,
        description="Maximum tree depth for base learners.",
        ge=1,
    )
    learning_rate: float = Field(
        default=0.1,
        description="Boosting learning rate.",
        gt=0.0,
        le=1.0,
    )
    subsample: float = Field(
        default=1.0,
        description="Subsample ratio of the training instances.",
        gt=0.0,
        le=1.0,
    )
    random_state: int = Field(
        default=42,
        description="Random seed for reproducibility.",
    )


ModelConfig = Annotated[
    ProphetModelConfig | XGBoostModelConfig,
    Field(discriminator="type"),
]
