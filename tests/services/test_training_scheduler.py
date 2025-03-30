from service_ml_forecast.services.training_scheduler import TrainingScheduler
from tests.conftest import cleanup_test_configs


def test_training_scheduler_init_start_stop() -> None:
    # Ensure any test configs are removed
    cleanup_test_configs()

    training_scheduler = TrainingScheduler()

    training_scheduler.start()
    assert training_scheduler.scheduler.running

    training_scheduler.stop()
    assert not training_scheduler.scheduler.running
