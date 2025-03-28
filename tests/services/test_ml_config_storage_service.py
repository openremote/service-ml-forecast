from service_ml_forecast.models.ml_config import ProphetMLConfig
from service_ml_forecast.services.ml_config_storage_service import MLConfigStorageService


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
