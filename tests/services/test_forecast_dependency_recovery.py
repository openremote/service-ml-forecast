"""Transient Manager outages recover through the real scheduler, without live writes."""

import datetime
import threading
from types import SimpleNamespace
from typing import TypedDict
from unittest.mock import Mock

import pytest
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED, JobExecutionEvent
from apscheduler.schedulers.background import BackgroundScheduler

from service_ml_forecast.common.exceptions import ResourceValidationError
from service_ml_forecast.services import model_scheduler as module


class RecoveryState(TypedDict):
    calls: int
    published: str
    after_failure: str | None


EXPECTED_QUICK_RETRIES = 3
EXPECTED_RECOVERY_CALLS = 2


def harness() -> tuple[module.ModelScheduler, SimpleNamespace]:
    config = SimpleNamespace(enabled=True)
    fake = module.ModelScheduler(Mock())
    fake.scheduler = Mock()
    fake.scheduler.get_job.return_value = SimpleNamespace(args=[config])
    return fake, config


def event(error: Exception | None = None, job: str = "model:forecast:one") -> JobExecutionEvent:
    return JobExecutionEvent(
        EVENT_JOB_ERROR if error else EVENT_JOB_EXECUTED,
        job,
        "default",
        datetime.datetime.now(datetime.UTC),
        exception=error,
    )


@pytest.mark.parametrize(
    "error",
    [
        ConnectionRefusedError("Manager starting"),
        TimeoutError("Manager timeout"),
    ],
)
def test_transient_failure_retries_existing_job_and_success_resets_budget(error: Exception) -> None:
    fake, _ = harness()
    for _ in range(8):
        module.ModelScheduler._on_forecast_job_event(fake, event(error))
    assert fake.scheduler.modify_job.call_count == EXPECTED_QUICK_RETRIES
    assert not fake.scheduler.add_job.called
    module.ModelScheduler._on_forecast_job_event(fake, event())
    module.ModelScheduler._on_forecast_job_event(fake, event(error))
    assert fake.scheduler.modify_job.call_count == EXPECTED_QUICK_RETRIES + 1


@pytest.mark.parametrize(
    "error",
    [
        ResourceValidationError("Invalid provider output"),
        ResourceValidationError("Required historical weather is unavailable"),
        ValueError("invalid model"),
    ],
)
def test_invalid_outputs_and_genuine_missing_data_do_not_spin_in_retry_loop(error: Exception) -> None:
    fake, _ = harness()
    module.ModelScheduler._on_forecast_job_event(fake, event(error))
    fake.scheduler.modify_job.assert_not_called()


def test_disabled_removed_and_nonforecast_jobs_are_not_resurrected() -> None:
    fake, config = harness()
    config.enabled = False
    module.ModelScheduler._on_forecast_job_event(fake, event(ConnectionRefusedError()))
    fake.scheduler.get_job.return_value = None
    module.ModelScheduler._on_forecast_job_event(fake, event(ConnectionRefusedError()))
    module.ModelScheduler._on_forecast_job_event(fake, event(ConnectionRefusedError(), "model:training:one"))
    fake.scheduler.modify_job.assert_not_called()


def test_actual_scheduler_recovers_without_waiting_for_next_hour(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(module, "FORECAST_RECOVERY_DELAY_SECONDS", 0.03)
    scheduler = BackgroundScheduler(executors={"default": {"type": "threadpool", "max_workers": 1}})
    fake = module.ModelScheduler(Mock())
    fake.scheduler = scheduler
    config = SimpleNamespace(enabled=True)
    done = threading.Event()
    state: RecoveryState = {"calls": 0, "published": "previous-valid-forecast", "after_failure": None}

    def forecast(_: SimpleNamespace) -> None:
        state["calls"] += 1
        if state["calls"] == 1:
            state["after_failure"] = state["published"]
            raise ConnectionError("Manager starting")
        state["published"] = "new-valid-forecast"
        done.set()

    scheduler.add_listener(
        lambda e: module.ModelScheduler._on_forecast_job_event(fake, e), EVENT_JOB_ERROR | EVENT_JOB_EXECUTED
    )
    scheduler.add_job(
        forecast,
        "interval",
        hours=1,
        args=[config],
        id="model:forecast:one",
        next_run_time=datetime.datetime.now(datetime.UTC),
    )
    scheduler.start()
    try:
        assert done.wait(3), "The transient failure must recover without a manual rerun"
        assert state["calls"] == EXPECTED_RECOVERY_CALLS
        assert state["after_failure"] == "previous-valid-forecast"
        assert state["published"] == "new-valid-forecast"
        assert len(scheduler.get_jobs()) == 1
        assert scheduler.get_job("model:forecast:one").trigger.interval == datetime.timedelta(hours=1)
    finally:
        scheduler.shutdown(wait=True)
