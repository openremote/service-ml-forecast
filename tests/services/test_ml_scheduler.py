from service_ml_forecast.clients.openremote.openremote_client import OpenRemoteClient
from service_ml_forecast.services.ml_job_scheduler import MLJobScheduler
from tests.conftest import cleanup_test_configs


def test_training_scheduler_init_start_stop(openremote_client: OpenRemoteClient) -> None:
    cleanup_test_configs()

    ml_job_scheduler = MLJobScheduler(openremote_client)

    ml_job_scheduler.start()
    assert ml_job_scheduler.scheduler.running

    ml_job_scheduler.stop()
    assert not ml_job_scheduler.scheduler.running
