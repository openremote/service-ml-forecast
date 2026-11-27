"""Quarantined source identities remain unsafe after the storage UTC migration."""

from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from service_ml_forecast.common.exceptions import ResourceValidationError
from service_ml_forecast.config import ENV, HistoryExclusion
from service_ml_forecast.services.openremote_service import OpenRemoteService


class MockClientService(OpenRemoteService):
    client: Mock


@pytest.fixture
def service(monkeypatch: pytest.MonkeyPatch) -> MockClientService:
    monkeypatch.setattr(ENV, "ML_OR_DATAPOINT_TIMEZONE", "UTC")
    monkeypatch.setattr(
        ENV,
        "ML_OR_HISTORY_EXCLUSIONS",
        [
            HistoryExclusion(
                asset_id="measured",
                attribute_name="power",
                first_ms=1000,
                last_ms=2000,
                reason="Original source-hour identity unavailable",
            )
        ],
    )
    result = MockClientService(Mock())
    result.client.assets.get_historical_datapoints.return_value = []
    return result


@pytest.mark.parametrize(("first", "last"), [(1000, 1000), (2000, 2000), (0, 1000), (2000, 3000), (0, 3000)])
def test_overlap_blocks_before_native_read(service: MockClientService, first: int, last: int) -> None:
    with pytest.raises(ResourceValidationError, match="excluded source history"):
        service._get_historical_datapoints("measured", "power", first, last)
    service.client.assets.get_historical_datapoints.assert_not_called()


@pytest.mark.parametrize(
    ("asset", "attr", "first", "last"),
    [
        ("fixture", "power", 1000, 2000),
        ("measured", "wind", 1000, 2000),
        ("measured", "power", 0, 999),
        ("measured", "power", 2001, 3000),
    ],
)
def test_other_assets_attributes_and_disjoint_windows_remain_usable(
    service: MockClientService, asset: str, attr: str, first: int, last: int
) -> None:
    assert service._get_historical_datapoints(asset, attr, first, last) == []


@pytest.mark.parametrize("change", [{"last_ms": 999}, {"first_ms": -1}, {"reason": ""}, {"extra": True}])
def test_invalid_exclusion_configuration_fails_validation(change: dict[str, object]) -> None:
    data = {
        "asset_id": "measured",
        "attribute_name": "power",
        "first_ms": 1000,
        "last_ms": 2000,
        "reason": "quarantined",
    }
    with pytest.raises(ValidationError):
        HistoryExclusion.model_validate(data | change)
