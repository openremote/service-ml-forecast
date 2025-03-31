from service_ml_forecast.clients.openremote.openremote_client import OpenRemoteClient
from service_ml_forecast.models.ml_model_config import ProphetModelConfig
from service_ml_forecast.services.ml_model_config_service import MLModelConfigService
from service_ml_forecast.services.ml_model_scheduler import MLModelScheduler
from tests.conftest import cleanup_test_configs

# Ensure clean configs directory
cleanup_test_configs()


def test_ml_model_scheduler_init_start_stop(openremote_client: OpenRemoteClient) -> None:
    model_scheduler = MLModelScheduler(openremote_client)

    model_scheduler.start()
    assert model_scheduler.scheduler.running

    # Assert whether any jobs have been added
    assert len(model_scheduler.scheduler.get_jobs()) > 0

    model_scheduler.stop()
    assert not model_scheduler.scheduler.running
    assert len(model_scheduler.scheduler.get_jobs()) == 0


def test_ml_model_scheduler_with_model_config(
    openremote_client: OpenRemoteClient, config_service: MLModelConfigService, prophet_basic_config: ProphetModelConfig
) -> None:
    model_scheduler = MLModelScheduler(openremote_client)

    # Save a config for training
    assert config_service.save(prophet_basic_config)

    # Start the scheduler
    model_scheduler.start()
    assert model_scheduler.scheduler.running

    expected_jobs = 2  # 1 for the base (refresh configs) job and 1 for the training job
    assert len(model_scheduler.scheduler.get_jobs()) == expected_jobs

    # Stop the scheduler
    model_scheduler.stop()
    assert not model_scheduler.scheduler.running
    assert len(model_scheduler.scheduler.get_jobs()) == 0
