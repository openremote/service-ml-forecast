import pytest

from service_ml_forecast.models.ml_model_config import MLModelFeature, MLModelType, ProphetMLModelConfig
from service_ml_forecast.services.ml_config_storage_service import MLConfigStorageService


@pytest.fixture
def prophet_test_config() -> ProphetMLModelConfig:
    return ProphetMLModelConfig(
        id="76b5a26f-a00f-4147-90ce-7e5d9dd8f91c",
        name="Test Config",
        realm="master",
        type=MLModelType.PROPHET,
        target=MLModelFeature(
            asset_id="test-asset-id", attribute_name="test-attribute-name", cutoff_timestamp=1716153600000
        ),
        forecast_interval="PT1H",
        training_interval="PT1D",
        forecast_periods=7,
        forecast_frequency="1h",
    )


def test_save_config(
    ml_config_storage_service: MLConfigStorageService, prophet_test_config: ProphetMLModelConfig
) -> None:
    assert ml_config_storage_service.save_config(prophet_test_config)
    assert ml_config_storage_service.get_config(prophet_test_config.id) is not None


def test_get_all_configs(ml_config_storage_service: MLConfigStorageService) -> None:
    configs = ml_config_storage_service.get_all_configs()
    assert configs is not None
    print(configs)
    assert len(configs) > 0


def test_update_config(
    ml_config_storage_service: MLConfigStorageService, prophet_test_config: ProphetMLModelConfig
) -> None:
    prophet_test_config.name = "Updated Config"
    assert ml_config_storage_service.update_config(prophet_test_config)
    config = ml_config_storage_service.get_config(prophet_test_config.id)
    assert config is not None
    assert config.name == "Updated Config"


def test_delete_config(
    ml_config_storage_service: MLConfigStorageService, prophet_test_config: ProphetMLModelConfig
) -> None:
    assert ml_config_storage_service.delete_config(prophet_test_config.id)
    assert ml_config_storage_service.get_config(prophet_test_config.id) is None
