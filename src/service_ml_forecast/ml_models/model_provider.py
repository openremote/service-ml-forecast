from typing import Protocol


class ModelProvider(Protocol):
    """Base protocol for all ML models.

    This protocol defines the methods that all ML model providers must implement.
    """

    def train_model(self) -> bool:
        pass

    def generate_forecast(self) -> bool:
        pass
