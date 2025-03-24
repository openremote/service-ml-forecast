from pydantic_settings import BaseSettings, SettingsConfigDict


class AppEnvironment(BaseSettings):
    """Application environment settings.

    All settings can be overridden via environment variables.
    """

    # Application Settings
    PUBLISH_DOCS: bool = True
    MODELS_DIR: str = "/data/models"
    CONFIGS_DIR: str = "/data/configs"

    # Logging
    LOG_LEVEL: str = "INFO"

    # Environment
    ENV: str = "development"

    # OpenRemote Settings
    OPENREMOTE_URL: str
    OPENREMOTE_KEYCLOAK_URL: str
    OPENREMOTE_SERVICE_USER: str
    OPENREMOTE_SERVICE_USER_SECRET: str

    model_config = SettingsConfigDict(case_sensitive=True, env_prefix="", env_file=".env", env_file_encoding="utf-8")

    def is_production(self) -> bool:
        """Check if the environment is production."""
        return self.ENV == "production"

    def is_development(self) -> bool:
        """Check if the environment is development."""
        return self.ENV == "development"


env = AppEnvironment()  # type: ignore  # noqa: PGH003
