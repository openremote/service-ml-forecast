from service_ml_forecast.clients.openremote.openremote_client import OpenRemoteClient
from service_ml_forecast.services.ml_model_scheduler import MLModelScheduler
from tests.conftest import cleanup_test_configs


def test_training_scheduler_init_start_stop(openremote_client: OpenRemoteClient) -> None:
    cleanup_test_configs()

    model_scheduler = MLModelScheduler(openremote_client)

    model_scheduler.start()
    assert model_scheduler.scheduler.running

    model_scheduler.stop()
    assert not model_scheduler.scheduler.running
