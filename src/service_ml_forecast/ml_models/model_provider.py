from typing import Protocol


class ModelProvider(Protocol):
    """Base protocol for all ML models.

    This protocol defines the methods that all ML model providers must implement.
    """

    def train(self) -> bool:
        pass

    def predict(self) -> bool:
        pass
