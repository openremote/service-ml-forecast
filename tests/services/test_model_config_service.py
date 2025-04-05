from uuid import uuid4

import pytest

from service_ml_forecast.common.exceptions import ResourceNotFoundError
from service_ml_forecast.models.model_config import ProphetModelConfig
from service_ml_forecast.services.model_config_service import ModelConfigService


def test_save_config(config_service: ModelConfigService, prophet_basic_config: ProphetModelConfig) -> None:
    """Test saving a new model configuration.

    Verifies that:
    - The configuration is successfully saved
    - The saved configuration can be retrieved
    """
    assert config_service.save(prophet_basic_config)
    assert config_service.get(prophet_basic_config.id) is not None


def test_get_config(config_service: ModelConfigService, prophet_basic_config: ProphetModelConfig) -> None:
    """Test retrieving a specific model configuration by ID.

    Verifies that:
    - A saved configuration can be retrieved by its ID
    - The retrieved configuration matches the original
    """
    assert config_service.save(prophet_basic_config)
    config = config_service.get(prophet_basic_config.id)
    assert config is not None
    assert config.id == prophet_basic_config.id


def test_get_config_not_found(config_service: ModelConfigService) -> None:
    """Test behavior when retrieving a non-existent configuration.

    Verifies that:
    - Requesting a configuration with an unknown ID returns None
    - The system handles non-existent configurations gracefully
    """
    with pytest.raises(ResourceNotFoundError):
        config_service.get(uuid4())


def test_get_all_configs(config_service: ModelConfigService, prophet_basic_config: ProphetModelConfig) -> None:
    """Test retrieving all model configurations.

    Verifies that:
    - All saved configurations can be retrieved as a collection
    - The collection is non-empty when configurations exist
    """
    assert config_service.save(prophet_basic_config)
    configs = config_service.get_all()
    assert configs is not None
    assert len(configs) > 0


def test_get_all_configs_with_realm(
    config_service: ModelConfigService, prophet_basic_config: ProphetModelConfig
) -> None:
    """Test retrieving all model configurations with a specific realm.

    Verifies that:
    - All saved configurations for the specified realm can be retrieved
    - The collection is non-empty when configurations exist for the realm
    """
    prophet_basic_config.realm = "test"
    assert config_service.save(prophet_basic_config)
    configs = config_service.get_all(realm="test")
    assert configs is not None
    assert len(configs) > 0

    configs = config_service.get_all(realm="non-existent")
    assert configs is not None
    assert len(configs) == 0


def test_update_config(config_service: ModelConfigService, prophet_basic_config: ProphetModelConfig) -> None:
    """Test updating an existing model configuration.

    Verifies that:
    - An existing configuration can be updated with new values
    - The updated values are persisted and can be retrieved
    """
    assert config_service.save(prophet_basic_config) is not None

    prophet_basic_config.name = "Updated Config"
    assert config_service.update(prophet_basic_config)

    config = config_service.get(prophet_basic_config.id)
    assert config is not None
    assert config.name == "Updated Config"


def test_delete_config(config_service: ModelConfigService, prophet_basic_config: ProphetModelConfig) -> None:
    """Test deleting a model configuration.

    Verifies that:
    - A configuration can be successfully deleted
    - The deleted configuration is no longer retrievable
    """
    assert config_service.save(prophet_basic_config) is not None

    config_service.delete(prophet_basic_config.id)

    with pytest.raises(ResourceNotFoundError):
        config_service.get(prophet_basic_config.id)
