"""Logging configuration for the application."""

from service_ml_forecast.config import env

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s %(levelname)s [%(name)s:%(lineno)d] - %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        }
    },
    "handlers": {
        "default": {
            "level": env.LOG_LEVEL,
            "formatter": "standard",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        }
    },
    "loggers": {
        "": {
            "handlers": ["default"],
            "level": env.LOG_LEVEL,
            "propagate": False,
        },
        "uvicorn": {"handlers": ["default"], "level": env.LOG_LEVEL, "propagate": False},
        "uvicorn.error": {
            "handlers": ["default"],
            "level": env.LOG_LEVEL,
            "propagate": False,
        },
        "uvicorn.access": {
            "handlers": ["default"],
            "level": env.LOG_LEVEL,
            "propagate": False,
        },
    },
}
