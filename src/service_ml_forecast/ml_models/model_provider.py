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
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from collections.abc import Callable
from typing import Protocol, TypeAlias

from service_ml_forecast.ml_models.model_util import ForecastResult, TrainingFeatureSet

SaveModelCallable: TypeAlias = Callable[[], bool]


class ModelProvider(Protocol):
    """Base protocol for all ML models.

    This protocol defines the methods that all ML model providers must implement.
    """

    def train_model(self, training_dataset: TrainingFeatureSet) -> SaveModelCallable | None:
        pass

    def generate_forecast(self) -> ForecastResult | None:
        pass
