from uuid import uuid4

import pytest

from service_ml_forecast.common.exceptions import ResourceNotFoundError, ResourceValidationError
from service_ml_forecast.models.model_config import FutureAssetDatapointFeature, ProphetModelConfig
from service_ml_forecast.services.model_config_service import ModelConfigService


def test_save_config(config_service: ModelConfigService, prophet_basic_config: ProphetModelConfig) -> None:
    """Test saving a new model configuration.

    Verifies that:
    - The configuration is successfully saved
    - The saved configuration can be retrieved
    """
    assert config_service.create(prophet_basic_config.realm, prophet_basic_config)
    assert config_service.get(prophet_basic_config.realm, prophet_basic_config.id) is not None


def test_get_config(config_service: ModelConfigService, prophet_basic_config: ProphetModelConfig) -> None:
    """Test retrieving a specific model configuration by ID.

    Verifies that:
    - A saved configuration can be retrieved by its ID
    - The retrieved configuration matches the original
    """
    assert config_service.create(prophet_basic_config.realm, prophet_basic_config)
    config = config_service.get(prophet_basic_config.realm, prophet_basic_config.id)
    assert config is not None
    assert config.id == prophet_basic_config.id


def test_get_config_not_found(config_service: ModelConfigService) -> None:
    """Test behavior when retrieving a non-existent configuration.

    Verifies that:
    - Requesting a configuration with an unknown ID returns None
    - The system handles non-existent configurations gracefully
    """
    with pytest.raises(ResourceNotFoundError):
        config_service.get("master", uuid4())


def test_get_all_configs(config_service: ModelConfigService, prophet_basic_config: ProphetModelConfig) -> None:
    """Test retrieving all model configurations.

    Verifies that:
    - All saved configurations can be retrieved as a collection
    - The collection is non-empty when configurations exist
    """
    assert config_service.create(prophet_basic_config.realm, prophet_basic_config)
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
    assert config_service.create(prophet_basic_config.realm, prophet_basic_config)
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
    assert config_service.create(prophet_basic_config.realm, prophet_basic_config) is not None

    prophet_basic_config.name = "Updated Config"
    assert config_service.update(prophet_basic_config.realm, prophet_basic_config.id, prophet_basic_config)

    config = config_service.get(prophet_basic_config.realm, prophet_basic_config.id)
    assert config is not None
    assert config.name == "Updated Config"


@pytest.mark.parametrize("dependency", ["target", "regressor"])
def test_update_config_rejects_assets_outside_its_realm(
    config_service: ModelConfigService,
    prophet_basic_config: ProphetModelConfig,
    monkeypatch: pytest.MonkeyPatch,
    dependency: str,
) -> None:
    config_service.create(prophet_basic_config.realm, prophet_basic_config)
    updated = prophet_basic_config.model_copy(deep=True)
    unavailable_asset_id = "44ORIhkDVAlT97dYGUD9n5"
    if dependency == "target":
        updated.target.asset_id = unavailable_asset_id
    else:
        updated.regressors = [
            FutureAssetDatapointFeature(
                asset_id=unavailable_asset_id,
                attribute_name="temperature",
                training_data_period=updated.target.training_data_period,
            )
        ]

    def available_assets(realm: str, asset_ids: list[str]) -> list[dict[str, str]]:
        return [{"id": asset_id, "realm": realm} for asset_id in asset_ids if asset_id != unavailable_asset_id]

    monkeypatch.setattr(config_service.openremote_service, "get_assets_by_ids", available_assets)

    with pytest.raises(ResourceValidationError, match="assets do not exist or are not in the correct realm"):
        config_service.update(updated.realm, updated.id, updated)

    assert config_service.get(prophet_basic_config.realm, prophet_basic_config.id) == prophet_basic_config


def test_delete_config(config_service: ModelConfigService, prophet_basic_config: ProphetModelConfig) -> None:
    """Test deleting a model configuration.

    Verifies that:
    - A configuration can be successfully deleted
    - The deleted configuration is no longer retrievable
    """
    assert config_service.create(prophet_basic_config.realm, prophet_basic_config) is not None

    config_service.delete(prophet_basic_config.realm, prophet_basic_config.id)

    with pytest.raises(ResourceNotFoundError):
        config_service.get(prophet_basic_config.realm, prophet_basic_config.id)


def test_only_one_enabled_writer_per_target(
    config_service: ModelConfigService, prophet_basic_config: ProphetModelConfig
) -> None:
    config_service.create(prophet_basic_config.realm, prophet_basic_config)
    second = prophet_basic_config.model_copy(update={"id": uuid4(), "name": "Second model", "enabled": False})
    config_service.create(second.realm, second)

    with pytest.raises(ResourceValidationError, match="already owned"):
        config_service.update(second.realm, second.id, second.model_copy(update={"enabled": True}))
    assert not config_service.get(second.realm, second.id).enabled

    with pytest.raises(ResourceValidationError, match="already owned"):
        config_service.create(
            second.realm,
            second.model_copy(update={"id": uuid4(), "enabled": True}),
        )

    config_service.update(
        prophet_basic_config.realm,
        prophet_basic_config.id,
        prophet_basic_config.model_copy(update={"enabled": False}),
    )
    config_service.update(second.realm, second.id, second.model_copy(update={"enabled": True}))
    assert config_service.get(second.realm, second.id).enabled
