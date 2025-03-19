import time

import pytest
from httpx import HTTPStatusError

from service_ml_forecast.integrations.openremote.models import (
    Asset,
    AssetDatapointPeriod,
    Datapoint,
)
from service_ml_forecast.integrations.openremote.openremote_client import OpenRemoteClient

# Tests won't work if there is no local OpenRemote Demo instance running


class TestOpenRemoteClient:
    def setup_class(self) -> None:
        from service_ml_forecast.config import config

        self.openremote_client = OpenRemoteClient(
            openremote_url=config.OPENREMOTE_URL,
            keycloak_url=config.OPENREMOTE_KEYCLOAK_URL,
            service_user=config.OPENREMOTE_SERVICE_USER,
            service_user_secret=config.OPENREMOTE_SERVICE_USER_SECRET,
        )

        self.test_asset_id = "44ORIhkDVAlT97dYGUD9n5"
        self.test_attribute_name = "powerTotalConsumers"

        if not self.openremote_client.health_check():
            pytest.skip(allow_module_level=True, reason="OpenRemote API not available")

    def test_retrieve_assets(self) -> None:
        assets: list[Asset] = self.openremote_client.retrieve_assets("master")
        assert len(assets) > 0, "Failed to retrieve assets"

    def test_retrieve_assets_invalid_realm(self) -> None:
        with pytest.raises(HTTPStatusError):
            self.openremote_client.retrieve_assets("invalid_realm_name")

    def test_retrieve_asset_datapoint_period(self) -> None:
        datapoint_period: AssetDatapointPeriod = self.openremote_client.retrieve_asset_datapoint_period(
            self.test_asset_id, self.test_attribute_name
        )
        assert datapoint_period is not None, "Failed to retrieve asset datapoint period"

    def test_retrieve_asset_datapoint_period_invalid_asset_id(self) -> None:
        with pytest.raises(HTTPStatusError):
            self.openremote_client.retrieve_asset_datapoint_period("invalid_asset_id", self.test_attribute_name)

    def test_retrieve_historical_datapoints(self) -> None:
        datapoints: list[Datapoint] = self.openremote_client.retrieve_historical_datapoints(
            self.test_asset_id, self.test_attribute_name, 1716153600000, int(time.time() * 1000)
        )
        assert len(datapoints) > 0, "Failed to retrieve historical datapoints"

    def test_retrieve_historical_datapoints_invalid_asset_id(self) -> None:
        with pytest.raises(HTTPStatusError):
            self.openremote_client.retrieve_historical_datapoints(
                "invalid_asset_id", self.test_attribute_name, 1716153600000, int(time.time() * 1000)
            )

    def test_write_retrieve_predicted_datapoints(self) -> None:
        timestamp1 = 572127577200000  # 20100-01-01 00:00:00
        timestamp2 = 572127577200001  # 20100-01-01 00:00:01

        datapoints: list[Datapoint] = [
            Datapoint(x=timestamp1, y=100),
            Datapoint(x=timestamp2, y=200),
        ]

        assert self.openremote_client.write_predicted_datapoints(
            self.test_asset_id, self.test_attribute_name, datapoints
        ), "Failed to write predicted datapoints"

        predicted_datapoints: list[Datapoint] = self.openremote_client.retrieve_predicted_datapoints(
            self.test_asset_id, self.test_attribute_name, timestamp1, timestamp2
        )
        assert len(predicted_datapoints) == len(datapoints), (
            "Predicted datapoints should have the same length as the written datapoints"
        )

        # Sort both lists by timestamp (x) before comparison
        sorted_predicted = sorted(predicted_datapoints, key=lambda d: d.x)
        sorted_original = sorted(datapoints, key=lambda d: d.x)

        for predicted_datapoint, datapoint in zip(sorted_predicted, sorted_original, strict=True):
            assert predicted_datapoint.x == datapoint.x, f"Timestamp mismatch: {predicted_datapoint.x} != {datapoint.x}"
            assert predicted_datapoint.y == datapoint.y, f"Value mismatch: {predicted_datapoint.y} != {datapoint.y}"
