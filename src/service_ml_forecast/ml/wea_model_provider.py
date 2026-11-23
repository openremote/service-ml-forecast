# Copyright 2026, OpenRemote Inc.
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

"""Weighted exponential average over raw historical observations.

Inputs retain their raw timestamps: no interpolation or averaging is performed.
Periods are elapsed UTC durations, including across daylight saving changes.
"""

from __future__ import annotations

import json
import math
from bisect import bisect_right
from dataclasses import asdict, dataclass
from datetime import timedelta
from pathlib import Path
from typing import cast
from uuid import UUID

import pandas as pd
from isodate import parse_duration
from openremote_client import AssetDatapoint

from service_ml_forecast.common.time_util import TimeUtil
from service_ml_forecast.ml.evaluation_metrics import EvaluationMetrics
from service_ml_forecast.models.feature_data_wrappers import ForecastDataSet, ForecastResult, TrainingDataSet
from service_ml_forecast.models.model_config import WEAModelConfig
from service_ml_forecast.services.model_storage_service import ModelStorageService


@dataclass
class WEAModel:
    timestamps: list[int]
    values: list[float]
    issue_ms: int
    step_ms: int
    period_ms: int
    count: int
    horizon: int

    @property
    def training_cutoff(self) -> str:
        return pd.Timestamp(self.timestamps[-1], unit="ms").isoformat()

    def save(self, path: Path) -> None:
        Path(path).write_text(json.dumps(asdict(self), allow_nan=False), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> WEAModel:
        return cls(**json.loads(Path(path).read_text(encoding="utf-8")))

    def predict(self) -> list[AssetDatapoint]:
        width = self.horizon * self.step_ms
        buckets: list[tuple[list[int], list[float]]] = []
        for index in range(self.count, 0, -1):
            begin = self.issue_ms - index * self.period_ms
            # Inclusive shared endpoints belong to the first (older) bucket.
            lower = begin + (1 if width == self.period_ms and index < self.count else 0)
            end = begin + width
            start_pos = bisect_right(self.timestamps, lower - 1)
            end_pos = bisect_right(self.timestamps, end)
            buckets.append((self.timestamps[start_pos:end_pos], self.values[start_pos:end_pos]))
        points = []
        alpha = 2.0 / (self.count + 1)
        for lead in range(1, self.horizon + 1):
            samples = []
            for index, (times, values) in zip(range(self.count, 0, -1), buckets, strict=True):
                sample_ms = self.issue_ms + lead * self.step_ms - index * self.period_ms
                pos = bisect_right(times, sample_ms) - 1
                if pos < 0:
                    raise ValueError(f"WEA missing historical sample for lead {lead}, past period {index}")
                samples.append(values[pos])
            estimate = samples[0]
            for value in samples[1:]:
                estimate = value * alpha + estimate * (1 - alpha)
            if not math.isfinite(estimate):
                raise ValueError("WEA produced a non-finite prediction")
            points.append(AssetDatapoint(x=self.issue_ms + lead * self.step_ms, y=estimate))
        return points


class WEAModelProvider:
    def __init__(self, config: WEAModelConfig) -> None:
        self.config = config
        self.model_storage_service = ModelStorageService()

    def train_model(self, training_dataset: TrainingDataSet) -> WEAModel:
        if training_dataset.covariates:
            raise ValueError("WEA uses target history only")
        raw = training_dataset.target.datapoints
        if not raw:
            raise ValueError("WEA requires target history")
        points: dict[int, float] = {}
        now = TimeUtil.get_timestamp_ms()
        for point in raw:
            if point.y is None or not math.isfinite(float(point.y)):
                raise ValueError("WEA target contains non-finite values")
            if point.x > now:
                raise ValueError("WEA target contains future observations")
            value = float(point.y)
            if point.x in points and points[point.x] != value:
                raise ValueError("WEA target has conflicting duplicate timestamps")
            points[point.x] = value
        times = sorted(points)
        step_ms = pd.tseries.frequencies.to_offset(self.config.forecast_frequency).nanos // 1_000_000
        model = WEAModel(
            timestamps=times,
            values=[points[t] for t in times],
            issue_ms=times[-1] // step_ms * step_ms,
            step_ms=step_ms,
            period_ms=int(cast(timedelta, parse_duration(self.config.past_period)).total_seconds() * 1000),
            count=self.config.past_count,
            horizon=self.config.forecast_periods,
        )
        # Do not publish an artifact that cannot supply the complete forecast.
        model.predict()
        return model

    def save_model(self, model: WEAModel) -> None:
        self.model_storage_service.save(model, self.config.id, self.config)

    def load_model(self, model_config_id: UUID) -> WEAModel:
        return self.model_storage_service.load(WEAModel, model_config_id, self.config)

    def generate_forecast(self, forecast_dataset: ForecastDataSet | None = None) -> ForecastResult:
        if forecast_dataset and forecast_dataset.covariates:
            raise ValueError("WEA does not accept forecast covariates")
        model = self.load_model(self.config.id)
        return ForecastResult(
            asset_id=self.config.target.asset_id,
            attribute_name=self.config.target.attribute_name,
            datapoints=model.predict(),
        )

    def evaluate_model(self, model: WEAModel) -> EvaluationMetrics | None:
        return None
