# Copyright 2025, OpenRemote Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from service_ml_forecast.config import ENV

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s %(levelname)s [%(name)s:%(lineno)d] - %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "default": {
            "level": ENV.ML_LOG_LEVEL,
            "formatter": "standard",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
    },
    "loggers": {
        # Service ML Forecast logs
        "": {
            "handlers": ["default"],
            "level": ENV.ML_LOG_LEVEL,
            "propagate": False,
        },
        # Allow APScheduler to propagate logs (e.g. for logging from worker processes)
        "apscheduler": {
            "handlers": [],
            "level": ENV.ML_LOG_LEVEL,
            "propagate": True,
        },
        # Uvicorn web server logs
        "uvicorn": {
            "handlers": [],
            "level": ENV.ML_LOG_LEVEL,
            "propagate": True
        },
        "uvicorn.error": {
            "handlers": [],
            "level": ENV.ML_LOG_LEVEL,
            "propagate": True,
        },
        "uvicorn.access": {
            "handlers": [],
            "level": ENV.ML_LOG_LEVEL,
            "propagate": True,
        },
    },
}
