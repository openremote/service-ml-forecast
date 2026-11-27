# Copyright 2025, OpenRemote Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import datetime
import threading
from unittest.mock import Mock

import pytest
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.schedulers.background import BackgroundScheduler

from service_ml_forecast.models.model_config import ProphetModelConfig
from service_ml_forecast.services import model_scheduler as module
from service_ml_forecast.services.model_config_service import ModelConfigService
from service_ml_forecast.services.openremote_service import OpenRemoteService


def scheduler(service: OpenRemoteService) -> module.ModelScheduler:
    result = module.ModelScheduler(service)
    result.scheduler = BackgroundScheduler(
        executors={
            "process_pool": ThreadPoolExecutor(max_workers=1),
            "thread_pool": ThreadPoolExecutor(max_workers=1),
        }
    )
    result.scheduler.add_listener(result._on_training_job_event, EVENT_JOB_ERROR | EVENT_JOB_EXECUTED)
    result.scheduler.add_listener(result._on_forecast_job_event, EVENT_JOB_ERROR | EVENT_JOB_EXECUTED)
    return result


def assert_training_precedes_forecast(subject: module.ModelScheduler, config: ProphetModelConfig) -> None:
    training_job = subject.scheduler.get_job(f"{module.TRAINING_JOB_ID_PREFIX}:{config.id}")
    forecast_job = subject.scheduler.get_job(f"{module.FORECAST_JOB_ID_PREFIX}:{config.id}")
    assert training_job is not None and forecast_job is not None
    assert training_job.next_run_time < forecast_job.next_run_time


def test_hourly_bootstrap_reuses_models_and_retrains_material_changes(
    monkeypatch: pytest.MonkeyPatch,
    mock_openremote_service: OpenRemoteService,
    config_service: ModelConfigService,
    prophet_basic_config: ProphetModelConfig,
) -> None:
    config = prophet_basic_config.model_copy(update={"forecast_interval": "PT1H"})
    config_service.create(config.realm, config)
    state = {"ready": False, "training": 0, "forecasts": 0}
    published = threading.Event()

    def train(*_: object) -> None:
        state["training"] += 1
        state["ready"] = True

    def forecast(*_: object) -> None:
        assert state["ready"]
        state["forecasts"] += 1
        published.set()

    monkeypatch.setattr(module, "_model_training_job", train)
    monkeypatch.setattr(module, "_model_forecast_job", forecast)
    monkeypatch.setattr(module.ModelScheduler, "_model_is_ready", staticmethod(lambda _: state["ready"]))
    first = scheduler(mock_openremote_service)
    first.start()
    try:
        assert published.wait(3), "Initial publication must not wait for the one-hour interval"
        for _ in range(5):
            first._poll_configs()
        assert state["training"] == state["forecasts"] == 1
        assert {job.id for job in first.scheduler.get_jobs()} == {
            module.CONFIG_WATCHER_JOB_ID,
            f"{module.TRAINING_JOB_ID_PREFIX}:{config.id}",
            f"{module.FORECAST_JOB_ID_PREFIX}:{config.id}",
        }
        for kind in (module.TRAINING_JOB_ID_PREFIX, module.FORECAST_JOB_ID_PREFIX):
            job = first.scheduler.get_job(f"{kind}:{config.id}")
            assert job is not None
            assert job.trigger.interval == datetime.timedelta(hours=1)
        assert_training_precedes_forecast(first, config)
    finally:
        first.stop()

    published.clear()
    second = scheduler(mock_openremote_service)
    second.start()
    try:
        assert published.wait(3), "A restart must publish using the compatible saved model"
        assert state["training"] == 1
        assert_training_precedes_forecast(second, config)
        published.clear()
        config.target.training_data_period = "P7D"
        config_service.update(config.realm, config.id, config)
        state["ready"] = False
        second._poll_configs()
        assert published.wait(3), "Material edits must promptly retrain and publish"
        expected_training_attempts = 2
        assert state["training"] == expected_training_attempts
        config.enabled = False
        config_service.update(config.realm, config.id, config)
        second._poll_configs()
        assert len(second.scheduler.get_jobs()) == 1
    finally:
        second.stop()


def test_failed_initial_training_waits_for_regular_interval(
    monkeypatch: pytest.MonkeyPatch,
    mock_openremote_service: OpenRemoteService,
    config_service: ModelConfigService,
    prophet_basic_config: ProphetModelConfig,
) -> None:
    config = prophet_basic_config.model_copy(update={"forecast_interval": "PT1H"})
    config_service.create(config.realm, config)
    attempted = threading.Event()
    calls: list[str] = []
    forecast = Mock()

    def train(*_: object) -> None:
        calls.append("train")
        attempted.set()
        raise ValueError("Insufficient historical data")

    monkeypatch.setattr(module, "_model_training_job", train)
    monkeypatch.setattr(module, "_model_forecast_job", forecast)
    monkeypatch.setattr(module.ModelScheduler, "_model_is_ready", staticmethod(lambda _: False))
    subject = scheduler(mock_openremote_service)
    subject.start()
    try:
        assert attempted.wait(3)
        for _ in range(5):
            subject._poll_configs()
        config.name = "Renamed after a failed attempt"
        config_service.update(config.realm, config.id, config)
        subject._poll_configs()
        job = subject.scheduler.get_job(f"{module.TRAINING_JOB_ID_PREFIX}:{config.id}")
        assert job is not None
        assert job.next_run_time > datetime.datetime.now(datetime.UTC) + datetime.timedelta(minutes=59)
        assert calls == ["train"]
        forecast.assert_not_called()
    finally:
        subject.stop()


def test_disabled_config_has_no_initial_attempt(
    mock_openremote_service: OpenRemoteService,
    config_service: ModelConfigService,
    prophet_basic_config: ProphetModelConfig,
) -> None:
    config = prophet_basic_config.model_copy(update={"enabled": False, "forecast_interval": "PT1H"})
    config_service.create(config.realm, config)
    subject = scheduler(mock_openremote_service)
    subject.start()
    try:
        assert [job.id for job in subject.scheduler.get_jobs()] == [module.CONFIG_WATCHER_JOB_ID]
    finally:
        subject.stop()


def test_edit_during_initial_training_starts_the_replacement_promptly(
    monkeypatch: pytest.MonkeyPatch,
    mock_openremote_service: OpenRemoteService,
    config_service: ModelConfigService,
    prophet_basic_config: ProphetModelConfig,
) -> None:
    config = prophet_basic_config.model_copy(update={"forecast_interval": "PT1H"})
    config_service.create(config.realm, config)
    started = threading.Event()
    release = threading.Event()
    published = threading.Event()
    trained: list[str] = []
    ready = threading.Event()

    def train(value: ProphetModelConfig, _: object) -> None:
        trained.append(value.target.training_data_period)
        if len(trained) == 1:
            started.set()
            assert release.wait(3)
        else:
            ready.set()

    def forecast(*_: object) -> None:
        assert ready.is_set()
        published.set()

    monkeypatch.setattr(module, "_model_training_job", train)
    monkeypatch.setattr(module, "_model_forecast_job", forecast)
    monkeypatch.setattr(module.ModelScheduler, "_model_is_ready", staticmethod(lambda _: ready.is_set()))
    subject = scheduler(mock_openremote_service)
    subject.start()
    try:
        assert started.wait(3)
        old_period = config.target.training_data_period
        config.target.training_data_period = "P7D"
        config_service.update(config.realm, config.id, config)
        subject._poll_configs()
        release.set()
        assert published.wait(3), "A superseded running job must not defer its replacement for an hour"
        assert trained == [old_period, "P7D"]
        assert not subject._initial_forecasts
    finally:
        release.set()
        subject.stop()
