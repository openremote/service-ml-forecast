"""Logging configuration for the application."""

import logging.config

from service_ml_forecast.config import config


def configure_logging() -> None:
    """Configure application-wide logging"""
    logging_config = {
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
                "level": config.LOG_LEVEL,
                "formatter": "standard",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
            }
        },
        "loggers": {
            "": {
                "handlers": ["default"],
                "level": config.LOG_LEVEL,
                "propagate": False,
            },
            "uvicorn": {"handlers": ["default"], "level": config.LOG_LEVEL, "propagate": False},
            "uvicorn.error": {
                "handlers": ["default"],
                "level": config.LOG_LEVEL,
                "propagate": False,
            },
            "uvicorn.access": {
                "handlers": ["default"],
                "level": config.LOG_LEVEL,
                "propagate": False,
            },
        },
    }
    logging.config.dictConfig(logging_config)
