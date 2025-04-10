import datetime
from http import HTTPStatus
from uuid import uuid4

import pytest
import respx

from service_ml_forecast.clients.openremote.models import AssetDatapoint
from service_ml_forecast.common.exceptions import ResourceNotFoundError
from service_ml_forecast.common.time_util import TimeUtil
from service_ml_forecast.ml.model_provider_factory import ModelProviderFactory
from service_ml_forecast.models.model_config import ProphetModelConfig
from service_ml_forecast.services.model_config_service import ModelConfigService
from service_ml_forecast.services.model_scheduler import (
    CONFIG_WATCHER_JOB_ID,
    FORECAST_JOB_ID_PREFIX,
    TRAINING_JOB_ID_PREFIX,
    ModelScheduler,
    _model_forecast_job,
    _model_training_job,
)
from service_ml_forecast.services.model_storage_service import ModelStorageService
from service_ml_forecast.services.openremote_data_service import OpenRemoteDataService
from tests.conftest import MOCK_OPENREMOTE_URL


def test_scheduler_lifecycle(mock_or_data_service: OpenRemoteDataService) -> None:
    """Test the initialization, starting and stopping of the MLModelScheduler.

    Verifies that:
    - The scheduler starts running correctly
    - The config watcher job is created
    - All jobs are removed when the scheduler stops
    """
    model_scheduler = ModelScheduler(mock_or_data_service)
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
    mock_or_data_service: OpenRemoteDataService,
    config_service: ModelConfigService,
    prophet_basic_config: ProphetModelConfig,
) -> None:
    """Test the scheduler behavior when a model configuration is present.

    Verifies that:
    - Training and forecast jobs are created for the config
    - Jobs have correct parameters and intervals
    - Jobs are properly removed when the config is deleted
    - Jobs are properly added when a config is created
    - Jobs are properly removed when the config is disabled
    - All jobs are properly cleaned up on stop
    """
    assert config_service.create(prophet_basic_config)
    model_scheduler = ModelScheduler(mock_or_data_service)
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
    assert training_job.func == _model_training_job
    expected_interval = datetime.timedelta(seconds=TimeUtil.parse_iso_duration(prophet_basic_config.training_interval))
    assert training_job.trigger.interval == expected_interval

    # Remove the config and check that the jobs are removed
    config_service.delete(prophet_basic_config.id)
    model_scheduler._poll_configs()
    assert model_scheduler.scheduler.get_job(f"{TRAINING_JOB_ID_PREFIX}:{prophet_basic_config.id}") is None
    assert model_scheduler.scheduler.get_job(f"{FORECAST_JOB_ID_PREFIX}:{prophet_basic_config.id}") is None

    # Re-add the config and check that the jobs are created
    assert config_service.create(prophet_basic_config)
    model_scheduler._poll_configs()
    assert model_scheduler.scheduler.get_job(f"{TRAINING_JOB_ID_PREFIX}:{prophet_basic_config.id}") is not None
    assert model_scheduler.scheduler.get_job(f"{FORECAST_JOB_ID_PREFIX}:{prophet_basic_config.id}") is not None

    # Disable the config and check that the jobs are removed
    prophet_basic_config.enabled = False
    assert config_service.update(prophet_basic_config)
    model_scheduler._poll_configs()
    assert model_scheduler.scheduler.get_job(f"{TRAINING_JOB_ID_PREFIX}:{prophet_basic_config.id}") is None
    assert model_scheduler.scheduler.get_job(f"{FORECAST_JOB_ID_PREFIX}:{prophet_basic_config.id}") is None

    # Stop the scheduler and check that the jobs are removed
    model_scheduler.stop()
    assert not model_scheduler.scheduler.running
    assert len(model_scheduler.scheduler.get_jobs()) == 0


def test_training_execution(
    mock_or_data_service: OpenRemoteDataService,
    config_service: ModelConfigService,
    prophet_basic_config: ProphetModelConfig,
    model_storage: ModelStorageService,
    windspeed_mock_datapoints: list[AssetDatapoint],
) -> None:
    """Test the execution of a training job with valid data.

    Verifies that:
    - The model is trained successfully with mock windspeed data
    - The trained model is properly stored
    """
    assert config_service.create(prophet_basic_config)

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
        _model_training_job(prophet_basic_config, mock_or_data_service)

    assert model_storage.get(prophet_basic_config.id, "json") is not None


def test_training_execution_with_missing_datapoints(
    mock_or_data_service: OpenRemoteDataService,
    config_service: ModelConfigService,
    prophet_basic_config: ProphetModelConfig,
    model_storage: ModelStorageService,
) -> None:
    """Test the training job behavior when no datapoints are available.

    Verifies that:
    - The system handles missing datapoints gracefully
    - No model is stored when training data is missing
    """
    prophet_basic_config.id = uuid4()  # override the id for this test
    assert config_service.create(prophet_basic_config)

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
        _model_training_job(prophet_basic_config, mock_or_data_service)

    with pytest.raises(ResourceNotFoundError):
        model_storage.get(prophet_basic_config.id, "json")


def test_forecast_execution(
    mock_or_data_service: OpenRemoteDataService,
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

        _model_forecast_job(trained_basic_model, mock_or_data_service)
        assert route.called


def test_forecast_execution_with_regressor(
    mock_or_data_service: OpenRemoteDataService,
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
    regressor_model = ModelProviderFactory.create_provider(trained_basic_model)
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

        _model_forecast_job(trained_regressor_model, mock_or_data_service)
        assert route.called


def test_forecast_execution_with_no_model(
    mock_or_data_service: OpenRemoteDataService,
    config_service: ModelConfigService,
    prophet_basic_config: ProphetModelConfig,
) -> None:
    """Test forecast behavior when no trained model is available.
    Verifies that:
    - System handles missing model gracefully
    - No predictions are written when model is missing
    """
    prophet_basic_config.id = uuid4()  # override the id for this test
    assert config_service.create(prophet_basic_config)

    with respx.mock(base_url=MOCK_OPENREMOTE_URL, assert_all_called=False) as respx_mock:
        # mock write predicted datapoints for target
        respx_mock.put(
            f"/api/master/asset/predicted/{prophet_basic_config.target.asset_id}/{prophet_basic_config.target.attribute_name}",
        ).mock(
            return_value=respx.MockResponse(HTTPStatus.NO_CONTENT),
        )

        with pytest.raises(ResourceNotFoundError):
            _model_forecast_job(prophet_basic_config, mock_or_data_service)


@pytest.fixture
def trained_basic_model(
    mock_or_data_service: OpenRemoteDataService,
    config_service: ModelConfigService,
    prophet_basic_config: ProphetModelConfig,
    windspeed_mock_datapoints: list[AssetDatapoint],
) -> ProphetModelConfig:
    """Fixture to create a trained basic model."""

    assert config_service.create(prophet_basic_config)

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
        _model_training_job(prophet_basic_config, mock_or_data_service)

    return prophet_basic_config


@pytest.fixture
def trained_regressor_model(
    mock_or_data_service: OpenRemoteDataService,
    config_service: ModelConfigService,
    prophet_multi_variable_config: ProphetModelConfig,
    windspeed_mock_datapoints: list[AssetDatapoint],
    tariff_mock_datapoints: list[AssetDatapoint],
) -> ProphetModelConfig:
    """Fixture to create a trained regressor model."""

    assert config_service.create(prophet_multi_variable_config)

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
        _model_training_job(prophet_multi_variable_config, mock_or_data_service)

    return prophet_multi_variable_config
