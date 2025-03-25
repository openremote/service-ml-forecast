import logging
import os
import tempfile

from pydantic import BaseModel

from service_ml_forecast.clients.openremote.models import AssetDatapoint
from service_ml_forecast.config import env

logger = logging.getLogger(__name__)


class FeatureDatapoints(BaseModel):
    """Dataset of datapoints with their attribute name."""

    attribute_name: str
    datapoints: list[AssetDatapoint]


class TrainingDataset(BaseModel):
    """Dataset of the target and regressors."""

    target: FeatureDatapoints
    regressors: list[FeatureDatapoints] | None = None


class ForecastResult(BaseModel):
    """Forecast result with the asset id, attribute name and the forecasted datapoints."""

    asset_id: str
    attribute_name: str
    datapoints: list[AssetDatapoint]


def save_model(model: str, path: str) -> bool:
    """Atomically save a model to a file."""

    file_path = f"{os.getcwd()}{env.MODELS_DIR}/{path}"
    dir_path = os.path.dirname(file_path)

    try:
        # Create directory if it doesn't exist
        os.makedirs(dir_path, exist_ok=True)

        with tempfile.NamedTemporaryFile(mode="w", dir=dir_path, delete=False) as temp_file:
            temp_file.write(model)
            temp_file.flush()
            os.fsync(temp_file.fileno())

            # Rename the temporary file to the target file
            os.replace(temp_file.name, file_path)

        logger.info(f"Saved model to {file_path}")
        return True
    except OSError:
        logger.error(f"Failed to save model to {file_path}")
        return False


def load_model(path: str) -> str | None:
    """Load a model from a file."""

    file_path = f"{os.getcwd()}{env.MODELS_DIR}/{path}"

    try:
        with open(file_path) as file:
            return file.read()
    except FileNotFoundError:
        logger.error(f"Failed to load model from {file_path}")
        return None


def delete_model(path: str) -> bool:
    """Delete a model from a file."""

    file_path = f"{os.getcwd()}{env.MODELS_DIR}/{path}"

    try:
        os.remove(file_path)
        logger.info(f"Deleted model from {file_path}")
        return True
    except OSError:
        logger.error(f"Failed to delete model from {file_path}")
        return False
