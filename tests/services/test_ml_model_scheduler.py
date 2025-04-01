import datetime
from http import HTTPStatus

import pytest
import respx

from service_ml_forecast.clients.openremote.models import AssetDatapoint
from service_ml_forecast.ml.ml_model_provider_factory import MLModelProviderFactory
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
from service_ml_forecast.services.openremote_ml_data_service import OpenRemoteMLDataService
from service_ml_forecast.util.time_util import TimeUtil
from tests.conftest import MOCK_OPENREMOTE_URL


def test_scheduler_lifecycle(mock_ml_data_service: OpenRemoteMLDataService) -> None:
    """Test the initialization, starting and stopping of the MLModelScheduler.

    Verifies that:
    - The scheduler starts running correctly
    - The config watcher job is created
    - All jobs are removed when the scheduler stops
    """

    model_scheduler = MLModelScheduler(mock_ml_data_service)
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


def test_scheduler_job_management(
    mock_ml_data_service: OpenRemoteMLDataService,
    config_service: MLModelConfigService,
    prophet_basic_config: ProphetModelConfig,
) -> None:
    """Test the scheduler behavior when a model configuration is present.

    Verifies that:
    - Training and forecast jobs are created for the config
    - Jobs have correct parameters and intervals
    - Jobs are properly removed when the config is deleted
    - All jobs are properly cleaned up on stop
    """

    assert config_service.save(prophet_basic_config)
    model_scheduler = MLModelScheduler(mock_ml_data_service)
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

    # Remove the config and check that the jobs are removed
    assert config_service.delete(prophet_basic_config.id)
    configs = config_service.get_all()
    model_scheduler._cleanup_stale_jobs(configs)  # trigger cleanup of stale jobs

    # Check that the jobs are removed
    assert model_scheduler.scheduler.get_job(f"{TRAINING_JOB_ID_PREFIX}:{prophet_basic_config.id}") is None
    assert model_scheduler.scheduler.get_job(f"{FORECAST_JOB_ID_PREFIX}:{prophet_basic_config.id}") is None

    # Stop the scheduler and check that the jobs are removed
    model_scheduler.stop()
    assert not model_scheduler.scheduler.running
    assert len(model_scheduler.scheduler.get_jobs()) == 0


def test_training_execution(
    mock_ml_data_service: OpenRemoteMLDataService,
    config_service: MLModelConfigService,
    prophet_basic_config: ProphetModelConfig,
    model_storage: MLModelStorageService,
    windspeed_mock_datapoints: list[AssetDatapoint],
) -> None:
    """Test the execution of a training job with valid data.

    Verifies that:
    - The model is trained successfully with mock windspeed data
    - The trained model is properly stored
    """

    assert config_service.save(prophet_basic_config)

    with respx.mock(base_url=MOCK_OPENREMOTE_URL) as respx_mock:
        # mock historical datapoints retrieval for target
        respx_mock.post(
            f"/api/master/asset/datapoint/{prophet_basic_config.target.asset_id}/{prophet_basic_config.target.attribute_name}",
        ).mock(
            return_value=respx.MockResponse(
                HTTPStatus.OK,
                json=windspeed_mock_datapoints,
            ),
        )
        _execute_ml_training(prophet_basic_config, mock_ml_data_service)

    assert model_storage.load(prophet_basic_config.id, ".json") is not None


def test_training_execution_with_missing_datapoints(
    mock_ml_data_service: OpenRemoteMLDataService,
    config_service: MLModelConfigService,
    prophet_basic_config: ProphetModelConfig,
    model_storage: MLModelStorageService,
) -> None:
    """Test the training job behavior when no datapoints are available.

    Verifies that:
    - The system handles missing datapoints gracefully
    - No model is stored when training data is missing
    """

    prophet_basic_config.id = "test"  # override the id for this test
    assert config_service.save(prophet_basic_config)

    with respx.mock(base_url=MOCK_OPENREMOTE_URL) as respx_mock:
        # mock historical datapoints retrieval for target with no datapoints
        respx_mock.post(
            f"/api/master/asset/datapoint/{prophet_basic_config.target.asset_id}/{prophet_basic_config.target.attribute_name}",
        ).mock(
            return_value=respx.MockResponse(
                HTTPStatus.OK,
                json=[],
            ),
        )
        _execute_ml_training(prophet_basic_config, mock_ml_data_service)

    assert model_storage.load(prophet_basic_config.id, ".json") is None


def test_forecast_execution(
    mock_ml_data_service: OpenRemoteMLDataService,
    trained_basic_model: ProphetModelConfig,
) -> None:
    """Test basic forecast execution with a single-variable model.
    Verifies that:
    - Forecast is generated successfully
    - Predicted datapoints are written to OpenRemote
    """

    with respx.mock(base_url=MOCK_OPENREMOTE_URL) as respx_mock:
        # mock write predicted datapoints for target
        route = respx_mock.put(
            f"/api/master/asset/predicted/{trained_basic_model.target.asset_id}/{trained_basic_model.target.attribute_name}",
        ).mock(
            return_value=respx.MockResponse(HTTPStatus.NO_CONTENT),
        )

        _execute_ml_forecast(trained_basic_model, mock_ml_data_service)
        assert route.called


def test_forecast_execution_with_regressor(
    mock_ml_data_service: OpenRemoteMLDataService,
    trained_regressor_model: ProphetModelConfig,
    trained_basic_model: ProphetModelConfig,
) -> None:
    """Test forecast execution with a multi-variable model using regressors.
    Verifies that:
    - Forecast is generated using regressor data
    - Regressor predictions are properly retrieved
    - Final predictions are written to OpenRemote
    """

    # get regressor model from basic trained model
    regressor_model = MLModelProviderFactory.create_provider(trained_basic_model)
    assert regressor_model is not None

    # generate forecast the regressor model
    regressor_forecast = regressor_model.generate_forecast()
    assert regressor_forecast is not None
    assert regressor_forecast.datapoints is not None
    assert len(regressor_forecast.datapoints) > 0

    regressor_forecast_datapoints = [datapoint.model_dump() for datapoint in regressor_forecast.datapoints]

    # config has regressors
    assert trained_regressor_model.regressors is not None
    assert len(trained_regressor_model.regressors) > 0

    with respx.mock(base_url=MOCK_OPENREMOTE_URL) as respx_mock:
        # mock write predicted datapoints for target
        route = respx_mock.put(
            f"/api/master/asset/predicted/{trained_regressor_model.target.asset_id}/{trained_regressor_model.target.attribute_name}",
        ).mock(
            return_value=respx.MockResponse(HTTPStatus.NO_CONTENT),
        )

        # mock predicted datapoints retrieval for regressor
        respx_mock.post(
            f"/api/master/asset/predicted/{trained_regressor_model.regressors[0].asset_id}/{trained_regressor_model.regressors[0].attribute_name}",
        ).mock(
            return_value=respx.MockResponse(HTTPStatus.OK, json=regressor_forecast_datapoints),
        )

        _execute_ml_forecast(trained_regressor_model, mock_ml_data_service)
        assert route.called


def test_forecast_execution_with_no_model(
    mock_ml_data_service: OpenRemoteMLDataService,
    config_service: MLModelConfigService,
    prophet_basic_config: ProphetModelConfig,
) -> None:
    """Test forecast behavior when no trained model is available.
    Verifies that:
    - System handles missing model gracefully
    - No predictions are written when model is missing
    """

    prophet_basic_config.id = "test"  # override the id for this test
    assert config_service.save(prophet_basic_config)

    with respx.mock(base_url=MOCK_OPENREMOTE_URL, assert_all_called=False) as respx_mock:
        # mock write predicted datapoints for target
        route = respx_mock.put(
            f"/api/master/asset/predicted/{prophet_basic_config.target.asset_id}/{prophet_basic_config.target.attribute_name}",
        ).mock(
            return_value=respx.MockResponse(HTTPStatus.NO_CONTENT),
        )

        _execute_ml_forecast(prophet_basic_config, mock_ml_data_service)
        assert not route.called


@pytest.fixture
def trained_basic_model(
    mock_ml_data_service: OpenRemoteMLDataService,
    config_service: MLModelConfigService,
    prophet_basic_config: ProphetModelConfig,
    windspeed_mock_datapoints: list[AssetDatapoint],
) -> ProphetModelConfig:
    """Fixture to create a trained basic model."""

    assert config_service.save(prophet_basic_config)

    with respx.mock(base_url=MOCK_OPENREMOTE_URL) as respx_mock:
        # mock historical datapoints retrieval for target
        respx_mock.post(
            f"/api/master/asset/datapoint/{prophet_basic_config.target.asset_id}/{prophet_basic_config.target.attribute_name}",
        ).mock(
            return_value=respx.MockResponse(
                HTTPStatus.OK,
                json=windspeed_mock_datapoints,
            ),
        )
        _execute_ml_training(prophet_basic_config, mock_ml_data_service)

    return prophet_basic_config


@pytest.fixture
def trained_regressor_model(
    mock_ml_data_service: OpenRemoteMLDataService,
    config_service: MLModelConfigService,
    prophet_multi_variable_config: ProphetModelConfig,
    windspeed_mock_datapoints: list[AssetDatapoint],
    tariff_mock_datapoints: list[AssetDatapoint],
) -> ProphetModelConfig:
    """Fixture to create a trained regressor model."""

    assert config_service.save(prophet_multi_variable_config)

    # assert that the model has regressors
    assert prophet_multi_variable_config.regressors is not None
    assert len(prophet_multi_variable_config.regressors) > 0

    with respx.mock(base_url=MOCK_OPENREMOTE_URL) as respx_mock:
        # mock historical datapoints retrieval for target
        respx_mock.post(
            f"/api/master/asset/datapoint/{prophet_multi_variable_config.target.asset_id}/{prophet_multi_variable_config.target.attribute_name}",
        ).mock(
            return_value=respx.MockResponse(
                HTTPStatus.OK,
                json=tariff_mock_datapoints,
            ),
        )
        # mock historical datapoints retrieval for regressor
        respx_mock.post(
            f"/api/master/asset/datapoint/{prophet_multi_variable_config.regressors[0].asset_id}/{prophet_multi_variable_config.regressors[0].attribute_name}",
        ).mock(
            return_value=respx.MockResponse(
                HTTPStatus.OK,
                json=windspeed_mock_datapoints,
            ),
        )
        _execute_ml_training(prophet_multi_variable_config, mock_ml_data_service)

    return prophet_multi_variable_config
