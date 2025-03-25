from pydantic_settings import BaseSettings, SettingsConfigDict


class AppEnvironment(BaseSettings):
    """Application environment settings.

    All settings can be overridden via environment variables.
    """

    # Application Settings
    PUBLISH_DOCS: bool = True
    MODELS_DIR: str = "/deployment/data/models"
    CONFIGS_DIR: str = "/deployment/data/configs"

    # Logging
    LOG_LEVEL: str = "INFO"

    # Environment
    ENV: str = "development"

    # OpenRemote Settings
    OPENREMOTE_URL: str = "http://localhost:8080"
    OPENREMOTE_KEYCLOAK_URL: str = "http://localhost:8081"
    OPENREMOTE_SERVICE_USER: str = "serviceuser"
    OPENREMOTE_SERVICE_USER_SECRET: str = "secret"

    model_config = SettingsConfigDict(case_sensitive=True, env_prefix="", env_file=".env", env_file_encoding="utf-8")

    def is_production(self) -> bool:
        """Check if the environment is production."""
        return self.ENV == "production"

    def is_development(self) -> bool:
        """Check if the environment is development."""
        return self.ENV == "development"


env = AppEnvironment()
