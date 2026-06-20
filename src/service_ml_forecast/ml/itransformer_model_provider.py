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

import base64
import io
import logging
from datetime import datetime
from uuid import UUID

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from openremote_client import AssetDatapoint
from torch.utils.data import DataLoader, Dataset, random_split

from service_ml_forecast.common.time_util import TimeUtil
from service_ml_forecast.ml._itransformer_net import ITransformerNet
from service_ml_forecast.ml.model_provider import ModelProvider
from service_ml_forecast.models.feature_data_wrappers import ForecastDataSet, ForecastResult, TrainingDataSet
from service_ml_forecast.models.model_config import ITransformerModelConfig
from service_ml_forecast.services.model_storage_service import ModelStorageService

logger = logging.getLogger(__name__)

_MODEL_FILE_EXT = "pt"

ITransformerBundle = dict  # state_dict + scaler + last window + hyperparams


class _TimeSeriesDataset(Dataset):  # type: ignore[type-arg]
    def __init__(self, features: np.ndarray, seq_len: int, pred_len: int) -> None:
        self.features = torch.from_numpy(features).float()
        self.seq_len = seq_len
        self.pred_len = pred_len

    def __len__(self) -> int:
        return len(self.features) - self.seq_len - self.pred_len + 1

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, torch.Tensor]:
        x = self.features[idx : idx + self.seq_len]
        y = self.features[idx + self.seq_len : idx + self.seq_len + self.pred_len, 0]
        return x, y


class ITransformerModelProvider(ModelProvider[ITransformerBundle]):
    """iTransformer model provider.

    Inverted Transformer for multivariate time series forecasting.
    Each variate's full time series is treated as a token; attention is over variates.
    Supports 6 built-in variates: z-scored target + hour_sin/cos + dow_sin/cos + is_weekend.
    Paper: https://arxiv.org/abs/2310.06625
    """

    def __init__(self, config: ITransformerModelConfig) -> None:
        self.config = config
        self.model_storage_service = ModelStorageService()
        self._device = "cuda" if torch.cuda.is_available() else "cpu"

    def train_model(self, training_dataset: TrainingDataSet) -> ITransformerBundle | None:
        datapoints = training_dataset.target.datapoints
        if not datapoints:
            logger.error("No target datapoints provided, cannot train model")
            return None

        min_required = self.config.seq_len + self.config.forecast_periods + 1
        if len(datapoints) < min_required:
            logger.error(
                f"Need at least {min_required} datapoints (seq_len + forecast_periods + 1), "
                f"got {len(datapoints)}"
            )
            return None

        logger.info(f"Training iTransformer -- {self.config.id} on {len(datapoints)} datapoints")

        features, timestamps_ms, mean, std = _build_feature_matrix(datapoints)
        pred_len = self.config.forecast_periods

        dataset = _TimeSeriesDataset(features, self.config.seq_len, pred_len)
        val_size = max(1, int(len(dataset) * self.config.val_split))
        train_size = len(dataset) - val_size
        train_ds, val_ds = random_split(dataset, [train_size, val_size])

        train_loader = DataLoader(train_ds, batch_size=self.config.batch_size, shuffle=True, drop_last=True)
        val_loader = DataLoader(val_ds, batch_size=self.config.batch_size, shuffle=False)

        model = ITransformerNet(
            seq_len=self.config.seq_len,
            pred_len=pred_len,
            d_model=self.config.d_model,
            n_heads=self.config.n_heads,
            n_layers=self.config.n_layers,
            d_ff=self.config.d_ff,
            dropout=self.config.dropout,
        ).to(self._device)

        optimizer = torch.optim.AdamW(model.parameters(), lr=self.config.lr, weight_decay=1e-4)
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=self.config.epochs)
        criterion = nn.MSELoss()

        best_val_loss = float("inf")
        best_state: dict = {}

        for epoch in range(1, self.config.epochs + 1):
            model.train()
            train_loss = 0.0
            for x, y in train_loader:
                x, y = x.to(self._device), y.to(self._device)
                optimizer.zero_grad()
                loss = criterion(model(x), y)
                loss.backward()
                nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                train_loss += loss.item()
            scheduler.step()

            model.eval()
            val_loss = 0.0
            with torch.no_grad():
                for x, y in val_loader:
                    x, y = x.to(self._device), y.to(self._device)
                    val_loss += criterion(model(x), y).item()

            train_loss /= len(train_loader)
            val_loss /= max(len(val_loader), 1)

            if val_loss < best_val_loss:
                best_val_loss = val_loss
                best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}

            if epoch % 5 == 0 or epoch == self.config.epochs:
                logger.info(f"Epoch {epoch:3d}/{self.config.epochs} | train {train_loss:.4f} | val {val_loss:.4f}")

        logger.info(f"Training complete -- {self.config.id} | best val MSE={best_val_loss:.4f}")

        last_window = datapoints[-self.config.seq_len :]

        return {
            "state_dict": best_state,
            "mean": float(mean),
            "std": float(std),
            "last_window": [(int(p.x), float(p.y)) for p in last_window],
            "seq_len": self.config.seq_len,
            "pred_len": pred_len,
            "d_model": self.config.d_model,
            "n_heads": self.config.n_heads,
            "n_layers": self.config.n_layers,
            "d_ff": self.config.d_ff,
            "dropout": self.config.dropout,
        }

    def save_model(self, model: ITransformerBundle) -> None:
        buf = io.BytesIO()
        torch.save(model, buf)
        encoded = base64.b64encode(buf.getvalue()).decode("utf-8")
        self.model_storage_service.save(encoded, self.config.id, model_file_extension=_MODEL_FILE_EXT)
        logger.info(f"Saved iTransformer -- {self.config.id}")

    def load_model(self, model_config_id: UUID) -> ITransformerBundle:
        encoded = self.model_storage_service.get(model_config_id, model_file_extension=_MODEL_FILE_EXT)
        buf = io.BytesIO(base64.b64decode(encoded))
        return torch.load(buf, map_location="cpu", weights_only=False)

    def generate_forecast(self, forecast_dataset: ForecastDataSet | None = None) -> ForecastResult:
        bundle = self.load_model(self.config.id)

        net = ITransformerNet(
            seq_len=bundle["seq_len"],
            pred_len=bundle["pred_len"],
            d_model=bundle["d_model"],
            n_heads=bundle["n_heads"],
            n_layers=bundle["n_layers"],
            d_ff=bundle["d_ff"],
            dropout=bundle["dropout"],
        ).to(self._device)
        net.load_state_dict(bundle["state_dict"])
        net.eval()

        mean: float = bundle["mean"]
        std: float = bundle["std"]
        last_window_raw: list[tuple[int, float]] = bundle["last_window"]

        window_datapoints = [AssetDatapoint(x=x, y=y) for x, y in last_window_raw]
        features, timestamps_ms, _, _ = _build_feature_matrix(window_datapoints, mean=mean, std=std)

        x = torch.from_numpy(features).float().unsqueeze(0).to(self._device)
        with torch.no_grad():
            pred_norm = net(x).squeeze(0).cpu().numpy()

        pred_values = pred_norm * std + mean

        freq_ms = _freq_to_ms(self.config.forecast_frequency)
        last_ts = int(timestamps_ms[-1])
        datapoints = [
            AssetDatapoint(x=last_ts + (i + 1) * freq_ms, y=float(v))
            for i, v in enumerate(pred_values)
        ]

        return ForecastResult(
            asset_id=self.config.target.asset_id,
            attribute_name=self.config.target.attribute_name,
            datapoints=datapoints,
        )


def _build_feature_matrix(
    datapoints: list[AssetDatapoint],
    mean: float | None = None,
    std: float | None = None,
) -> tuple[np.ndarray, np.ndarray, float, float]:
    """Convert raw AssetDatapoints to a 6-variate feature matrix."""
    sorted_pts = sorted(datapoints, key=lambda p: p.x)
    timestamps_ms = np.array([p.x for p in sorted_pts], dtype=np.int64)
    tariff = np.array([float(p.y) for p in sorted_pts], dtype=np.float32)

    if mean is None:
        mean = float(tariff.mean())
    if std is None:
        std = float(tariff.std()) + 1e-8

    tariff_norm = (tariff - mean) / std

    dts = [datetime.fromtimestamp(ts / 1000) for ts in timestamps_ms]
    hours = np.array([dt.hour for dt in dts], dtype=np.float32)
    days = np.array([dt.weekday() for dt in dts], dtype=np.float32)
    weekend = (days >= 5).astype(np.float32)

    features = np.stack(
        [
            tariff_norm,
            np.sin(2 * np.pi * hours / 24),
            np.cos(2 * np.pi * hours / 24),
            np.sin(2 * np.pi * days / 7),
            np.cos(2 * np.pi * days / 7),
            weekend,
        ],
        axis=1,
    )
    return features, timestamps_ms, mean, std


def _freq_to_ms(frequency: str) -> int:
    """Convert a pandas frequency string (e.g. '1h', '30min') to milliseconds."""
    offset = pd.tseries.frequencies.to_offset(frequency)
    if offset is None:
        raise ValueError(f"Unrecognised forecast_frequency: {frequency!r}")
    nanos: int = int(pd.Timedelta(offset).value)  # type: ignore[arg-type]
    return nanos // 1_000_000
