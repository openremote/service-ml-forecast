from service_ml_forecast.models.ml_config import ProphetMLConfig
from service_ml_forecast.services.ml_config_storage_service import MLConfigStorageService
from service_ml_forecast.services.training_scheduler import TrainingScheduler
from tests.conftest import cleanup_test_configs


def test_training_scheduler_init_with_no_configs() -> None:
    # Cleanup any existing configs
    cleanup_test_configs()

    training_scheduler = TrainingScheduler()
    assert len(training_scheduler.configs) == 0


def test_training_scheduler_init_with_configs(
    ml_config_storage_service: MLConfigStorageService, test_ml_config: ProphetMLConfig
) -> None:
    assert ml_config_storage_service.save_config(test_ml_config)

    training_scheduler = TrainingScheduler()
    assert len(training_scheduler.configs) == 1

    training_scheduler.start()
    assert training_scheduler.scheduler.running
