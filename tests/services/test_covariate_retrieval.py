"""Input retrieval respects future lags and the issue-time observation boundary."""

from unittest.mock import Mock

import pytest

from service_ml_forecast.common.time_util import TimeUtil
from service_ml_forecast.services.openremote_service import OpenRemoteService
from tests.ml.test_covariate_robustness import setup_case

ISSUE_TIME_MS = 123456789


@pytest.mark.parametrize("model_type", ["xgboost", "lightgbm"])
def test_retrieval_extends_future_lags_but_never_reads_future_observations(
    model_type: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    config, _, _ = setup_case(model_type)
    config.lags_future_covariates = [0, 2]
    client = Mock()
    client.assets.get_predicted_datapoints.return_value = []
    client.assets.get_historical_datapoints.return_value = []
    monkeypatch.setattr(TimeUtil, "get_timestamp_ms", lambda: ISSUE_TIME_MS)
    monkeypatch.setattr(TimeUtil, "get_period_start_timestamp_ms", lambda _: 1000)
    monkeypatch.setattr(TimeUtil, "pd_future_timestamp", lambda periods, _: periods * 3_600_000)
    OpenRemoteService(client).get_forecast_dataset(config)
    assert client.assets.get_predicted_datapoints.call_args.args[-1] == (config.forecast_periods + 2) * 3_600_000
    assert client.assets.get_historical_datapoints.call_args.args[-1] == ISSUE_TIME_MS
