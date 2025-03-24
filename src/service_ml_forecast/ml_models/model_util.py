import os

from pydantic import BaseModel

from service_ml_forecast.clients.openremote.models import AssetDatapoint
from service_ml_forecast.config import env


class DatapointWrapper(BaseModel):
    """Util class for wrapping datapoints with their attribute name."""

    attribute_name: str
    datapoints: list[AssetDatapoint]


def save_model(model: str, path: str) -> bool:
    """Save a model to a file."""

    file_path = f"{os.getcwd()}{env.MODELS_DIR}/{path}"

    try:
        with open(file_path, "w") as file:
            file.write(model)
    except FileNotFoundError:
        return False

    return True


def load_model(path: str) -> str | None:
    """Load a model from a file."""

    file_path = f"{os.getcwd()}{env.MODELS_DIR}/{path}"

    try:
        with open(file_path) as file:
            return file.read()
    except FileNotFoundError:
        return None
