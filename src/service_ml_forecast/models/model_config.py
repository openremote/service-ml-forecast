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

from pydantic import BaseModel, Field, model_validator

from service_ml_forecast.models.model_type import ModelTypeEnum


class RegressorAssetDatapointsFeature(BaseModel):
    """Asset regressor feature with the asset id, attribute name and the cutoff timestamp.

    The asset regressor is a covariate that is used to predict the target asset.
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

    # Used for model training and forecasting -- requiring unique feature name
    def get_feature_name(self) -> str:
        """Get the feature name for the regressor feature."""
        return f"{self.asset_id}.{self.attribute_name}"


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
    target: TargetAssetDatapointsFeature = Field(
        description="The asset attribute to generate datapoints for. "
        "There must be historical data available for training.",
    )
    regressors: list[RegressorAssetDatapointsFeature] | None = Field(
        default=None,
        description="List of optional asset attributes that will be used as regressors. "
        "There must be historical data available for training. "
        "There must also be future data available for forecasting.",
    )
    forecast_interval: str = Field(
        description="Forecast generation interval. "
        "Training is always executed before the forecast job. "
        "Expects ISO 8601 duration strings."
    )
    training_interval: str | None = Field(
        default=None,
        description="Deprecated. Use forecast_interval instead.",
        deprecated=True,
    )
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


class ITransformerModelConfig(BaseModelConfig):
    """iTransformer specific configuration."""

    type: Literal[ModelTypeEnum.ITRANSFORMER] = ModelTypeEnum.ITRANSFORMER
    seq_len: int = Field(
        default=96,
        description="Input lookback window in number of datapoints. Must be >= 2 × forecast_periods.",
        ge=2,
    )
    d_model: int = Field(default=128, description="Transformer embedding dimension.", ge=1)
    n_heads: int = Field(default=4, description="Number of attention heads.", ge=1)
    n_layers: int = Field(default=2, description="Number of encoder layers.", ge=1)
    d_ff: int = Field(default=256, description="Feed-forward hidden dimension.", ge=1)
    dropout: float = Field(default=0.1, description="Dropout rate.", ge=0.0, le=1.0)
    epochs: int = Field(default=30, description="Training epochs.", ge=1)
    batch_size: int = Field(default=64, description="Training batch size.", ge=1)
    lr: float = Field(default=1e-3, description="AdamW learning rate.", gt=0.0)
    val_split: float = Field(default=0.2, description="Fraction of data held out for validation.", ge=0.0, lt=1.0)


_REQUIRED_FEATURE_MAPPING_COLS: frozenset[str] = frozenset({
    "temperature_2m", "cloud_cover", "wind_speed_10m", "shortwave_radiation",
    "total_load", "generation_forecast", "Open", "High", "Low", "Change %",
})


class NLEnergyForecasterModelConfig(BaseModelConfig):
    """Pre-trained NL energy price forecaster (encoder-decoder transformer from HuggingFace).

    Inference-only: no local training. The sync job downloads the model from
    https://huggingface.co/Nazim112/nl-energy-forecaster and stores the last 168 h of
    feature data. Produces a fixed 24-step hourly price forecast (EUR/MWh).
    """

    type: Literal[ModelTypeEnum.NL_ENERGY_FORECASTER] = ModelTypeEnum.NL_ENERGY_FORECASTER
    feature_mapping: dict[str, str] = Field(
        description=(
            "Maps non-time, non-Price FEATURE_COL names to regressor feature_names "
            "(format: '{asset_id}.{attribute_name}'). "
            "Required keys: temperature_2m, cloud_cover, wind_speed_10m, shortwave_radiation, "
            "total_load, generation_forecast, Open, High, Low, 'Change %'. "
            "Time features (day, hour_sin/cos, day_of_week_sin/cos, month_sin/cos, "
            "quarter_sin/cos, weekend_sin/cos) are computed automatically. "
            "'Price' is always taken from the target attribute."
        )
    )

    @model_validator(mode="after")
    def validate_nl_config(self) -> "NLEnergyForecasterModelConfig":
        if self.forecast_periods != 24:
            raise ValueError(
                f"NL energy forecaster always produces exactly 24 forecast periods "
                f"(HORIZON=24), got forecast_periods={self.forecast_periods}"
            )
        missing = _REQUIRED_FEATURE_MAPPING_COLS - set(self.feature_mapping.keys())
        if missing:
            raise ValueError(
                f"feature_mapping is missing required keys: {sorted(missing)}"
            )
        return self


ModelConfig = Annotated[
    ProphetModelConfig | ITransformerModelConfig | NLEnergyForecasterModelConfig,
    Field(discriminator="type"),
]
