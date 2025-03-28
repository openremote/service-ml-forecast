import pytest

from service_ml_forecast.models.ml_config import MLFeature, MLModelType, ProphetMLConfig
from service_ml_forecast.services.ml_config_storage_service import MLConfigStorageService


@pytest.fixture
def ml_config_storage_service() -> MLConfigStorageService:
    return MLConfigStorageService()


@pytest.fixture
def test_ml_config() -> ProphetMLConfig:
    return ProphetMLConfig(
        id="test_config",
        name="Test Config",
        realm="master",
        type=MLModelType.PROPHET,
        target=MLFeature(
            asset_id="test-asset-id", attribute_name="test-attribute-name", cutoff_timestamp=1716153600000
        ),
        forecast_interval="PT1H",
        training_interval="PT1D",
        forecast_periods=7,
        forecast_frequency="1h",
    )


def test_save_config(ml_config_storage_service: MLConfigStorageService, test_ml_config: ProphetMLConfig) -> None:
    assert ml_config_storage_service.save_config(test_ml_config)
    assert ml_config_storage_service.get_config(test_ml_config.id) is not None


def test_get_all_configs(ml_config_storage_service: MLConfigStorageService, test_ml_config: ProphetMLConfig) -> None:
    configs = ml_config_storage_service.get_all_configs()
    assert configs is not None
    assert len(configs) > 0


def test_update_config(ml_config_storage_service: MLConfigStorageService, test_ml_config: ProphetMLConfig) -> None:
    test_ml_config.name = "Updated Config"
    assert ml_config_storage_service.update_config(test_ml_config)
    config = ml_config_storage_service.get_config(test_ml_config.id)
    assert config is not None
    assert config.name == "Updated Config"


def test_delete_config(ml_config_storage_service: MLConfigStorageService, test_ml_config: ProphetMLConfig) -> None:
    assert ml_config_storage_service.delete_config(test_ml_config.id)
    assert ml_config_storage_service.get_config(test_ml_config.id) is None
