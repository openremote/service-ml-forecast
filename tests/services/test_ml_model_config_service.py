from service_ml_forecast.models.ml_model_config import ProphetModelConfig
from service_ml_forecast.services.ml_model_config_service import MLModelConfigService
from tests.conftest import cleanup_test_configs

# Ensure clean configs directory
cleanup_test_configs()


def test_save_config(config_service: MLModelConfigService, prophet_basic_config: ProphetModelConfig) -> None:
    assert config_service.save(prophet_basic_config)
    assert config_service.get(prophet_basic_config.id) is not None


def test_get_config(config_service: MLModelConfigService, prophet_basic_config: ProphetModelConfig) -> None:
    config = config_service.get(prophet_basic_config.id)
    assert config is not None
    assert config.id == prophet_basic_config.id


def test_get_config_not_found(config_service: MLModelConfigService) -> None:
    config = config_service.get("non-existent-id")
    assert config is None


def test_get_all_configs(config_service: MLModelConfigService) -> None:
    configs = config_service.get_all()
    assert configs is not None
    print(configs)
    assert len(configs) > 0


def test_update_config(config_service: MLModelConfigService, prophet_basic_config: ProphetModelConfig) -> None:
    prophet_basic_config.name = "Updated Config"
    assert config_service.update(prophet_basic_config)
    config = config_service.get(prophet_basic_config.id)
    assert config is not None
    assert config.name == "Updated Config"


def test_delete_config(config_service: MLModelConfigService, prophet_basic_config: ProphetModelConfig) -> None:
    assert config_service.delete(prophet_basic_config.id)
    assert config_service.get(prophet_basic_config.id) is None
