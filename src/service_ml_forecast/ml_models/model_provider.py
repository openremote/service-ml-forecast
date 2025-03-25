from collections.abc import Callable
from typing import Protocol, TypeAlias

from service_ml_forecast.ml_models.model_util import ForecastResult, TrainingDataset

SaveModelCallable: TypeAlias = Callable[[], bool]


class ModelProvider(Protocol):
    """Base protocol for all ML models.

    This protocol defines the methods that all ML model providers must implement.
    """

    def train_model(self, training_dataset: TrainingDataset) -> SaveModelCallable | None:
        pass

    def generate_forecast(self) -> ForecastResult | None:
        pass
