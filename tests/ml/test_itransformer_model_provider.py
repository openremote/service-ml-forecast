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

from pydantic import TypeAdapter

from openremote_client import AssetDatapoint

from service_ml_forecast.ml.model_provider_factory import ModelProviderFactory
from service_ml_forecast.models.feature_data_wrappers import AssetFeatureDatapoints, TrainingDataSet
from service_ml_forecast.models.model_config import ITransformerModelConfig, ModelConfig


def test_train_and_predict(
    itransformer_config: ITransformerModelConfig,
    windspeed_mock_datapoints: list[AssetDatapoint],
) -> None:
    """Verifies that iTransformer trains, saves, loads, and forecasts correctly."""
    provider = ModelProviderFactory.create_provider(itransformer_config)

    model = provider.train_model(
        TrainingDataSet(
            target=AssetFeatureDatapoints(
                feature_name=itransformer_config.target.attribute_name,
                datapoints=windspeed_mock_datapoints,
            ),
        ),
    )
    assert model is not None

    provider.save_model(model)
    assert itransformer_config.id is not None
    assert provider.load_model(itransformer_config.id) is not None

    forecast = provider.generate_forecast()
    assert forecast is not None
    assert forecast.datapoints is not None
    assert len(forecast.datapoints) == itransformer_config.forecast_periods


def test_train_returns_none_on_insufficient_data(
    itransformer_config: ITransformerModelConfig,
) -> None:
    """train_model returns None when datapoints < seq_len + forecast_periods + 1."""
    provider = ModelProviderFactory.create_provider(itransformer_config)

    too_few = [AssetDatapoint(x=i * 3_600_000, y=float(i)) for i in range(5)]
    model = provider.train_model(
        TrainingDataSet(
            target=AssetFeatureDatapoints(
                feature_name=itransformer_config.target.attribute_name,
                datapoints=too_few,
            ),
        ),
    )
    assert model is None


def test_model_config_union_parses_itransformer() -> None:
    """ModelConfig discriminated union correctly deserializes an iTransformer config dict."""
    adapter = TypeAdapter(ModelConfig)
    raw = {
        "type": "itransformer",
        "realm": "master",
        "name": "Test",
        "target": {"asset_id": "41ORIhkDVAlT97dYGUD9n5", "attribute_name": "tariff"},
        "forecast_interval": "PT1H",
        "forecast_periods": 24,
        "forecast_frequency": "1h",
    }
    config = adapter.validate_python(raw)
    assert isinstance(config, ITransformerModelConfig)
    assert config.seq_len == 96


def test_train_returns_none_on_empty_data(
    itransformer_config: ITransformerModelConfig,
) -> None:
    """train_model returns None when no datapoints are provided."""
    provider = ModelProviderFactory.create_provider(itransformer_config)

    model = provider.train_model(
        TrainingDataSet(
            target=AssetFeatureDatapoints(
                feature_name=itransformer_config.target.attribute_name,
                datapoints=[],
            ),
        ),
    )
    assert model is None
