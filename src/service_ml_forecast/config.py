from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings.

    All settings can be overridden via environment variables.
    """

    # Application Settings
    PUBLIC_DOCS: bool = True

    # Logging
    LOG_LEVEL: str = "INFO"

    # Environment
    ENV: str = "development"

    # OpenRemote Settings
    OPENREMOTE_URL: Optional[str] = None
    OPENREMOTE_SERVICE_USER: Optional[str] = None
    OPENREMOTE_SERVICE_USER_SECRET: Optional[str] = None

    model_config = SettingsConfigDict(case_sensitive=True, env_prefix="")

    """
    Check if the environment is production
    """

    def is_production(self) -> bool:
        return self.ENV == "production"

    """
    Check if the environment is development
    """

    def is_development(self) -> bool:
        return self.ENV == "development"


config = Settings()
