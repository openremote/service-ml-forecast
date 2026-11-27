"""Prevent the observed repeated-hour corruption at the real service boundary."""

from datetime import datetime
from unittest.mock import Mock

import pytest
from openremote_client import AssetDatapoint

from service_ml_forecast.common.exceptions import ResourceValidationError
from service_ml_forecast.config import ENV
from service_ml_forecast.services.openremote_service import OpenRemoteService
from tests.services.test_model_artifact_lifecycle import config


class MockClientService(OpenRemoteService):
    client: Mock


def ms(value: str) -> int:
    return int(datetime.fromisoformat(value).timestamp() * 1000)


@pytest.fixture
def service(monkeypatch: pytest.MonkeyPatch) -> MockClientService:
    monkeypatch.setattr(ENV, "ML_OR_DATAPOINT_TIMEZONE", "Europe/Amsterdam", raising=False)
    return MockClientService(Mock())


@pytest.mark.parametrize(
    ("start", "end"),
    [
        ("2026-10-25T00:00:00+00:00", "2026-10-25T00:59:59+00:00"),
        ("2026-10-25T01:00:00+00:00", "2026-10-25T01:59:59+00:00"),
        ("2026-10-01T00:00:00+00:00", "2026-10-26T00:00:00+00:00"),
    ],
)
def test_ambiguous_history_window_never_queries_manager(service: MockClientService, start: str, end: str) -> None:
    with pytest.raises(ResourceValidationError, match="ambiguous"):
        service._get_historical_datapoints("asset", "power", ms(start), ms(end))
    service.client.assets.get_historical_datapoints.assert_not_called()


def test_source_response_outside_requested_utc_bounds_is_rejected(
    service: MockClientService, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(ENV, "ML_OR_DATAPOINT_TIMEZONE", "UTC")
    service.client.assets.get_historical_datapoints.return_value = [
        AssetDatapoint(x=ms("2026-10-25T01:10:00+00:00"), y=20)
    ]
    with pytest.raises(ResourceValidationError, match="outside"):
        service._get_historical_datapoints(
            "asset", "power", ms("2026-10-25T00:00:00+00:00"), ms("2026-10-25T00:59:59+00:00")
        )


@pytest.mark.parametrize("zone", ["Europe/Amsterdam", "Australia/Lord_Howe"])
def test_single_ambiguous_prediction_cannot_be_written(
    service: MockClientService, monkeypatch: pytest.MonkeyPatch, zone: str
) -> None:
    monkeypatch.setattr(ENV, "ML_OR_DATAPOINT_TIMEZONE", zone)
    instant = "2026-10-25T00:30:00+00:00" if zone == "Europe/Amsterdam" else "2026-04-04T15:10:00+00:00"
    with pytest.raises(ResourceValidationError, match="ambiguous"):
        service.write_predicted_datapoints(config("wea"), [AssetDatapoint(x=ms(instant), y=20)])
    service.client.assets.write_predicted_datapoints.assert_not_called()


@pytest.mark.parametrize("start", ["2027-03-28T00:00:00+00:00", "2026-10-26T00:00:00+00:00"])
def test_supported_write_is_read_back_exactly(service: MockClientService, start: str) -> None:
    points = [AssetDatapoint(x=ms(start) + i * 3_600_000, y=20 + i) for i in range(24)]
    service.client.assets.write_predicted_datapoints.return_value = True
    service.client.assets.get_predicted_datapoints.return_value = list(reversed(points))
    assert service.write_predicted_datapoints(config("wea"), points)
    service.client.assets.get_predicted_datapoints.assert_called_once()


@pytest.mark.parametrize("fault", ["missing", "changed", "timeout"])
def test_success_acknowledgement_does_not_hide_failed_readback(service: MockClientService, fault: str) -> None:
    points = [AssetDatapoint(x=ms("2026-10-26T00:00:00+00:00") + i * 3_600_000, y=20 + i) for i in range(24)]
    error: type[Exception]
    service.client.assets.write_predicted_datapoints.return_value = True
    if fault == "timeout":
        service.client.assets.get_predicted_datapoints.side_effect = TimeoutError("after commit")
        error = TimeoutError
    else:
        returned = points[:-1] if fault == "missing" else [p.model_copy(update={"y": p.y + 1}) for p in points]
        service.client.assets.get_predicted_datapoints.return_value = returned
        error = ResourceValidationError
    with pytest.raises(error):
        service.write_predicted_datapoints(config("wea"), points)


def test_failed_acknowledgement_does_not_read_back(service: MockClientService) -> None:
    service.client.assets.write_predicted_datapoints.return_value = False
    assert not service.write_predicted_datapoints(
        config("wea"), [AssetDatapoint(x=ms("2026-10-26T00:00:00+00:00"), y=20)]
    )
    service.client.assets.get_predicted_datapoints.assert_not_called()


def test_utc_transport_can_preserve_both_clock_occurrences(
    service: MockClientService, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(ENV, "ML_OR_DATAPOINT_TIMEZONE", "UTC")
    points = [AssetDatapoint(x=ms("2026-10-25T00:00:00+00:00") + i * 3_600_000, y=20 + i) for i in range(24)]
    service.client.assets.write_predicted_datapoints.return_value = True
    service.client.assets.get_predicted_datapoints.return_value = points
    assert service.write_predicted_datapoints(config("wea"), points)


def test_ambiguous_future_input_window_is_rejected(service: MockClientService) -> None:
    with pytest.raises(ResourceValidationError, match="ambiguous"):
        service._get_predicted_datapoints(
            "weather", "temperature", ms("2026-10-24T00:00:00+00:00"), ms("2026-10-26T00:00:00+00:00")
        )
    service.client.assets.get_predicted_datapoints.assert_not_called()
