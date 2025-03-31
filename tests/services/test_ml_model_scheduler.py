import datetime
from http import HTTPStatus

import respx

from service_ml_forecast.clients.openremote.models import AssetDatapoint
from service_ml_forecast.clients.openremote.openremote_client import OpenRemoteClient
from service_ml_forecast.models.ml_model_config import ProphetModelConfig
from service_ml_forecast.services.ml_model_config_service import MLModelConfigService
from service_ml_forecast.services.ml_model_scheduler import (
    CONFIG_WATCHER_JOB_ID,
    FORECAST_JOB_ID_PREFIX,
    TRAINING_JOB_ID_PREFIX,
    MLModelScheduler,
    _execute_ml_forecast,
    _execute_ml_training,
)
from service_ml_forecast.services.ml_model_storage_service import MLModelStorageService
from service_ml_forecast.util.time_util import TimeUtil
from tests.conftest import MOCK_OPENREMOTE_URL, cleanup_test_configs

# Ensure clean configs directory
cleanup_test_configs()


def test_ml_model_scheduler_init_start_stop(mock_openremote_client: OpenRemoteClient) -> None:
    model_scheduler = MLModelScheduler(mock_openremote_client)
    model_scheduler.start()

    assert model_scheduler.scheduler.running

    # It is expected that the config refresh job is always present
    expected_jobs = [
        CONFIG_WATCHER_JOB_ID,
    ]
    assert len(model_scheduler.scheduler.get_jobs()) == len(expected_jobs)
    for job in expected_jobs:
        assert model_scheduler.scheduler.get_job(job) is not None

    # Stop the scheduler and check that the jobs are removed
    model_scheduler.stop()
    assert not model_scheduler.scheduler.running
    assert len(model_scheduler.scheduler.get_jobs()) == 0


def test_ml_model_scheduler_config_present(
    mock_openremote_client: OpenRemoteClient,
    config_service: MLModelConfigService,
    prophet_basic_config: ProphetModelConfig,
) -> None:
    assert config_service.save(prophet_basic_config)
    model_scheduler = MLModelScheduler(mock_openremote_client)
    model_scheduler.start()

    assert model_scheduler.scheduler.running

    # It is expected that the training job has been added to the scheduler
    expected_jobs = [
        CONFIG_WATCHER_JOB_ID,
        f"{TRAINING_JOB_ID_PREFIX}:{prophet_basic_config.id}",
        f"{FORECAST_JOB_ID_PREFIX}:{prophet_basic_config.id}",
    ]
    assert len(model_scheduler.scheduler.get_jobs()) == len(expected_jobs)
    for job in expected_jobs:
        assert model_scheduler.scheduler.get_job(job) is not None

    # Training job has the correct parameters
    training_job = model_scheduler.scheduler.get_job(f"{TRAINING_JOB_ID_PREFIX}:{prophet_basic_config.id}")
    assert training_job is not None
    assert training_job.func == _execute_ml_training
    expected_interval = datetime.timedelta(seconds=TimeUtil.parse_iso_duration(prophet_basic_config.training_interval))
    assert training_job.trigger.interval == expected_interval

    # Stop the scheduler and check that the jobs are removed
    model_scheduler.stop()
    assert not model_scheduler.scheduler.running
    assert len(model_scheduler.scheduler.get_jobs()) == 0


def test_ml_model_scheduler_execute_training_job(
    mock_openremote_client: OpenRemoteClient,
    config_service: MLModelConfigService,
    prophet_basic_config: ProphetModelConfig,
    model_storage: MLModelStorageService,
    windspeed_mock_datapoints: list[AssetDatapoint],
) -> None:
    assert config_service.save(prophet_basic_config)

    # add mock for the forecast datapoints
    with respx.mock(base_url=MOCK_OPENREMOTE_URL) as respx_mock:
        respx_mock.post(
            f"/api/master/asset/datapoint/{prophet_basic_config.target.asset_id}/{prophet_basic_config.target.attribute_name}"
        ).mock(
            return_value=respx.MockResponse(
                HTTPStatus.OK,
                json=windspeed_mock_datapoints,
            )
        )
        _execute_ml_training(prophet_basic_config, mock_openremote_client)

    assert model_storage.load(prophet_basic_config.id, ".json") is not None


def test_ml_model_scheduler_execute_forecast_job(
    mock_openremote_client: OpenRemoteClient,
    config_service: MLModelConfigService,
    prophet_basic_config: ProphetModelConfig,
) -> None:
    assert config_service.save(prophet_basic_config)

    # add mock for writing forecast datapoints
    with respx.mock(base_url=MOCK_OPENREMOTE_URL) as respx_mock:
        respx_mock.put(
            f"/api/master/asset/predicted/{prophet_basic_config.target.asset_id}/{prophet_basic_config.target.attribute_name}"
        ).mock(
            return_value=respx.MockResponse(HTTPStatus.NO_CONTENT),
        )
        _execute_ml_forecast(prophet_basic_config, mock_openremote_client)
