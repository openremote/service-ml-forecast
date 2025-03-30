import pytest

from service_ml_forecast.models.ml_model_config import AssetAttributeFeature, ProphetModelConfig
from service_ml_forecast.models.ml_model_type import MLModelTypeEnum
from service_ml_forecast.services.ml_model_config_service import MLModelConfigService


@pytest.fixture
def prophet_test_config() -> ProphetModelConfig:
    return ProphetModelConfig(
        id="76b5a26f-a00f-4147-90ce-7e5d9dd8f91c",
        name="Test Config",
        realm="master",
        type=MLModelTypeEnum.PROPHET,
        target=AssetAttributeFeature(
            asset_id="test-asset-id", attribute_name="test-attribute-name", cutoff_timestamp=1716153600000
        ),
        forecast_interval="PT1H",
        training_interval="PT1D",
        forecast_periods=7,
        forecast_frequency="1h",
    )


def test_save_config(config_service: MLModelConfigService, prophet_test_config: ProphetModelConfig) -> None:
    assert config_service.save(prophet_test_config)
    assert config_service.get(prophet_test_config.id) is not None


def test_get_all_configs(config_service: MLModelConfigService) -> None:
    configs = config_service.get_all()
    assert configs is not None
    print(configs)
    assert len(configs) > 0


def test_update_config(config_service: MLModelConfigService, prophet_test_config: ProphetModelConfig) -> None:
    prophet_test_config.name = "Updated Config"
    assert config_service.update(prophet_test_config)
    config = config_service.get(prophet_test_config.id)
    assert config is not None
    assert config.name == "Updated Config"


def test_delete_config(config_service: MLModelConfigService, prophet_test_config: ProphetModelConfig) -> None:
    assert config_service.delete(prophet_test_config.id)
    assert config_service.get(prophet_test_config.id) is None
