from service_ml_forecast.services.ml_job_scheduler import MLJobScheduler
from tests.conftest import cleanup_test_configs


def test_training_scheduler_init_start_stop() -> None:
    # Ensure any test configs are removed
    cleanup_test_configs()

    ml_job_scheduler = MLJobScheduler()

    ml_job_scheduler.start()
    assert ml_job_scheduler.scheduler.running

    ml_job_scheduler.stop()
    assert not ml_job_scheduler.scheduler.running
