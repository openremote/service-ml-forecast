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

from datetime import timedelta
from enum import Enum
from typing import Annotated, Literal
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import pandas as pd
from isodate import parse_duration
from pydantic import BaseModel, Field, ValidationInfo, field_validator, model_validator

from service_ml_forecast.models.model_type import ModelTypeEnum

NANOSECONDS_PER_MILLISECOND = 1_000_000


class AssetDatapointFeature(BaseModel):
    """Base asset feature with the asset id, attribute name and the training data period.

    The asset feature is a covariate that is used for model training and forecasting.
    """

    asset_id: str = Field(description="ID of the asset from OpenRemote.", min_length=22, max_length=22)
    attribute_name: str = Field(
        description="Name of the attribute of the asset.",
        min_length=1,
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
        min_length=1,
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
    forecast_interval: str = Field(
        description="Forecast generation interval. "
        "Training is always executed before the forecast job. "
        "Expects ISO 8601 duration strings."
    )
    training_interval: str | None = Field(
        default=None,
        description="Deprecated. Uses forecast_interval now instead (train > forecast order). Model training interval. "
        "Expects ISO 8601 duration strings.",
        deprecated=True,
    )
    forecast_periods: int = Field(description="Number of periods to forecast.")
    forecast_frequency: str = Field(
        description="The frequency of each forecasted datapoint. "
        "Expects a pandas frequency string. E.g. '30min' or '1h'. "
        "Generated forecast datapoints are rounded to the nearest frequency. "
        "Example: 15:30 -> 16:00 -> 16:30 etc.",
    )
    calendar_timezone: str | None = Field(
        default=None,
        description="IANA timezone for cyclic local hour and day-of-week future regressors. "
        "When omitted, calendar regressors are disabled.",
    )

    @field_validator("calendar_timezone")
    @classmethod
    def validate_calendar_timezone(cls, value: str | None) -> str | None:
        if value is not None:
            try:
                ZoneInfo(value)
            except ZoneInfoNotFoundError as error:
                raise ValueError(f"Unknown calendar timezone: {value}") from error
        return value


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


class TreeModelConfig(BaseModelConfig):
    """Configuration shared by Darts tree-regression models."""

    forecast_periods: int = Field(description="Positive number of periods to forecast.", ge=1)
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
        default=168,
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
        default=0.8,
        description="Subsample ratio of the training instances.",
        gt=0.0,
        le=1.0,
    )
    random_state: int = Field(
        default=42,
        description="Random seed for reproducibility.",
    )

    @field_validator("lags", "lags_past_covariates", "lags_future_covariates", mode="before")
    @classmethod
    def validate_tree_lags(cls, value: object, info: ValidationInfo) -> object:
        if value is None:
            return value
        future = info.field_name == "lags_future_covariates"
        if not future and isinstance(value, int) and not isinstance(value, bool) and value > 0:
            return value
        if isinstance(value, list) and value:
            integers = all(isinstance(lag, int) and not isinstance(lag, bool) for lag in value)
            if integers and all(lag >= 0 if future else lag < 0 for lag in value):
                return value
        expected = "a non-empty list of zero or positive steps" if future else "a positive count or negative-step list"
        raise ValueError(f"{info.field_name} requires {expected}")

    @model_validator(mode="after")
    def validate_tree_window(self) -> "TreeModelConfig":
        try:
            step_ns = pd.tseries.frequencies.to_offset(self.forecast_frequency).nanos
        except (ValueError, TypeError) as error:
            raise ValueError("Tree forecast frequency must be a fixed duration") from error
        if step_ns < NANOSECONDS_PER_MILLISECOND or step_ns % NANOSECONDS_PER_MILLISECOND:
            raise ValueError("Tree forecast frequency must be positive and contain whole milliseconds")
        if all(value is None for value in (self.lags, self.lags_past_covariates, self.lags_future_covariates)):
            if self.calendar_timezone is None:
                raise ValueError("Tree models require target lags, covariate lags or calendar features")
        return self


class XGBoostModelConfig(TreeModelConfig):
    """XGBoost specific configuration."""

    type: Literal[ModelTypeEnum.XGBOOST] = ModelTypeEnum.XGBOOST


class LightGBMModelConfig(TreeModelConfig):
    """LightGBM specific configuration."""

    type: Literal[ModelTypeEnum.LIGHTGBM] = ModelTypeEnum.LIGHTGBM


class WEAModelConfig(BaseModelConfig):
    """Target-only weighted exponential average over fixed elapsed periods."""

    type: Literal[ModelTypeEnum.WEA] = ModelTypeEnum.WEA
    past_period: str = Field(default="P7D", description="Fixed ISO duration between historical samples.")
    past_count: int = Field(default=4, ge=1, le=100, description="Historical periods, oldest to newest.")

    @model_validator(mode="after")
    def validate_wea_window(self) -> "WEAModelConfig":
        period = parse_duration(self.past_period)
        if not isinstance(period, timedelta) or period.total_seconds() <= 0:
            raise ValueError("WEA past period must be a positive fixed duration, without months or years")
        try:
            step_ns = pd.tseries.frequencies.to_offset(self.forecast_frequency).nanos
        except ValueError as error:
            raise ValueError("WEA forecast frequency must be a fixed duration") from error
        if step_ns < NANOSECONDS_PER_MILLISECOND or step_ns % NANOSECONDS_PER_MILLISECOND or self.forecast_periods < 1:
            raise ValueError("WEA requires positive periods and a positive whole-millisecond frequency")
        period_ms = period.total_seconds() * 1000
        if not period_ms.is_integer():
            raise ValueError("WEA past period must contain whole milliseconds")
        if self.forecast_periods * step_ns > int(period.total_seconds() * 1_000_000_000):
            raise ValueError("WEA forecast horizon must not exceed the past period")
        if self.calendar_timezone is not None:
            raise ValueError("WEA uses elapsed-time periods and does not support calendar covariates")
        return self


ModelConfig = Annotated[
    ProphetModelConfig | XGBoostModelConfig | LightGBMModelConfig | WEAModelConfig,
    Field(discriminator="type"),
]
