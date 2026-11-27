"""Valid one-point covariate windows must retain their configured frequency."""

import math

import pytest

from service_ml_forecast.ml.model_provider_factory import ModelProviderFactory
from tests.ml.test_covariate_robustness import setup_case


@pytest.mark.parametrize("model_type", ["xgboost", "lightgbm"])
@pytest.mark.parametrize("mode", ["direct_past", "one_future_step", "one_calendar_step"])
def test_single_required_covariate_step_can_be_predicted(model_type: str, mode: str) -> None:
    config, training, future = setup_case(model_type, past=mode == "direct_past", future=mode == "one_future_step")
    if mode == "direct_past":
        config.output_chunk_length = config.forecast_periods
    else:
        config.forecast_periods = 1
        if mode == "one_future_step":
            config.calendar_timezone = None
    provider = ModelProviderFactory.create_provider(config)
    provider.save_model(provider.train_model(training))
    result = provider.generate_forecast(future)
    assert len(result.datapoints) == config.forecast_periods
    assert all(math.isfinite(point.y) for point in result.datapoints)
