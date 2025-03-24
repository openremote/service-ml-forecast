from service_ml_forecast.clients.openremote.openremote_client import OpenRemoteClient
from service_ml_forecast.ml_models.model_provider import ModelProvider
from service_ml_forecast.ml_models.prophet_model_provider import ProphetModelProvider
from service_ml_forecast.schemas.model_config import ModelConfig, ModelType, ProphetModelConfig


class ModelProviderFactory:
    """Factory for creating model providers based on the provided model config."""

    @staticmethod
    def create_provider(
        config: ModelConfig,
        openremote_client: OpenRemoteClient,
    ) -> ModelProvider:
        """Create a model provider instance based on the model config type.

        Args:
            config: The model configuration.
            openremote_client: The OpenRemote client for data access.
        """
        if config.type == ModelType.PROPHET:
            if not isinstance(config, ProphetModelConfig):
                raise ValueError(f"Expected ProphetModelConfig for model type {ModelType.PROPHET}")
            return ProphetModelProvider(config=config, openremote_client=openremote_client)

        raise ValueError(f"Unsupported model type: {config.type}")
