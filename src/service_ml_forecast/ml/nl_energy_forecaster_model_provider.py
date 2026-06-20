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

from __future__ import annotations

import base64
import io
import logging
from datetime import datetime
from pathlib import Path
from uuid import UUID

import joblib
import numpy as np
import pandas as pd
import torch
from openremote_client import AssetDatapoint

from service_ml_forecast.ml._enc_dec_transformer_net import EncDecModelConfig, EncoderDecoderTransformerModel, TransformerConfig
from service_ml_forecast.ml.model_provider import ModelProvider
from service_ml_forecast.models.feature_data_wrappers import ForecastDataSet, ForecastResult, TrainingDataSet
from service_ml_forecast.models.model_config import NLEnergyForecasterModelConfig
from service_ml_forecast.services.model_storage_service import ModelStorageService

logger = logging.getLogger(__name__)

HF_REPO_ID = "Nazim112/nl-energy-forecaster"
INPUT_LEN = 168
HORIZON = 24

FEATURE_COLS = [
    "temperature_2m",
    "cloud_cover",
    "wind_speed_10m",
    "shortwave_radiation",
    "total_load",
    "generation_forecast",
    "Price",
    "Open",
    "High",
    "Low",
    "Change %",
    "day",
    "hour_sin",
    "hour_cos",
    "day_of_week_sin",
    "day_of_week_cos",
    "month_sin",
    "month_cos",
    "quarter_sin",
    "quarter_cos",
    "weekend_sin",
    "weekend_cos",
]

_TIME_FEATURE_COLS = frozenset({
    "day", "hour_sin", "hour_cos", "day_of_week_sin", "day_of_week_cos",
    "month_sin", "month_cos", "quarter_sin", "quarter_cos", "weekend_sin", "weekend_cos",
})

_MODEL_FILE_EXT = "pt"

NLEnergyForecasterBundle = dict


class NLEnergyForecasterModelProvider(ModelProvider[NLEnergyForecasterBundle]):
    """Inference-only provider for the pre-trained NL energy price forecaster on HuggingFace.

    Training (sync) job downloads the model from HF and stores the last INPUT_LEN hours of
    feature data in the bundle. Forecast job loads the bundle and runs inference.
    Model repo: https://huggingface.co/Nazim112/nl-energy-forecaster
    """

    def __init__(self, config: NLEnergyForecasterModelConfig) -> None:
        self.config = config
        self.model_storage_service = ModelStorageService()
        self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    def train_model(self, training_dataset: TrainingDataSet) -> NLEnergyForecasterBundle | None:
        """Downloads the pre-trained model from HuggingFace and captures the feature window."""
        logger.info(f"Syncing NL energy forecaster {self.config.id} from HuggingFace ({HF_REPO_ID})")

        try:
            from huggingface_hub import snapshot_download  # noqa: PLC0415
            repo_dir = Path(snapshot_download(HF_REPO_ID))
        except Exception as e:
            logger.error(f"Failed to download model from HuggingFace: {e}")
            return None

        checkpoint = torch.load(repo_dir / "best_model.pt", map_location="cpu", weights_only=False)
        scalers = joblib.load(repo_dir / "scalers.joblib")

        # Build last_window: col_name → [(ts_ms, value), ...]
        last_window: dict[str, list[tuple[int, float]]] = {}

        price_pts = sorted(training_dataset.target.datapoints, key=lambda p: p.x)
        last_window["Price"] = [(int(p.x), float(p.y)) for p in price_pts[-INPUT_LEN:]]

        if training_dataset.regressors:
            # Reverse map: regressor feature_name → FEATURE_COL name
            reverse_map = {v: k for k, v in self.config.feature_mapping.items()}
            for reg in training_dataset.regressors:
                col_name = reverse_map.get(reg.feature_name)
                if col_name and col_name in FEATURE_COLS and col_name not in _TIME_FEATURE_COLS:
                    sorted_pts = sorted(reg.datapoints, key=lambda p: p.x)
                    last_window[col_name] = [(int(p.x), float(p.y)) for p in sorted_pts[-INPUT_LEN:]]

        missing_cols = [
            c for c in FEATURE_COLS
            if c not in _TIME_FEATURE_COLS and c not in last_window
        ]
        if missing_cols:
            logger.warning(
                f"NL energy forecaster {self.config.id}: missing feature data for {missing_cols}. "
                "Forecasts will use zeros for these features."
            )

        logger.info(f"NL energy forecaster {self.config.id} sync complete")
        return {
            "model_state_dict": checkpoint["model_state_dict"],
            "checkpoint_config": checkpoint["config"],
            "input_dim": checkpoint["input_dim"],
            "horizon": checkpoint["horizon"],
            "input_kind": checkpoint.get("input_kind", "sequence"),
            "target_scaler": scalers["target_scaler"],
            "feature_scaler": scalers["feature_scaler"],
            "last_window": last_window,
        }

    def save_model(self, model: NLEnergyForecasterBundle) -> None:
        buf = io.BytesIO()
        torch.save(model, buf)
        encoded = base64.b64encode(buf.getvalue()).decode("utf-8")
        self.model_storage_service.save(encoded, self.config.id, model_file_extension=_MODEL_FILE_EXT)
        logger.info(f"Saved NL energy forecaster bundle -- {self.config.id}")

    def load_model(self, model_config_id: UUID) -> NLEnergyForecasterBundle:
        encoded = self.model_storage_service.get(model_config_id, model_file_extension=_MODEL_FILE_EXT)
        buf = io.BytesIO(base64.b64decode(encoded))
        return torch.load(buf, map_location="cpu", weights_only=False)

    def generate_forecast(self, forecast_dataset: ForecastDataSet | None = None) -> ForecastResult:
        bundle = self.load_model(self.config.id)

        cfg_dict = bundle["checkpoint_config"]["model"]["transformer"]
        transformer_cfg = TransformerConfig(
            d_model=cfg_dict["d_model"],
            nhead=cfg_dict["nhead"],
            num_layers=cfg_dict["num_layers"],
            num_decoder_layers=cfg_dict.get("num_decoder_layers", cfg_dict["num_layers"]),
            dim_feedforward=cfg_dict["dim_feedforward"],
            dropout=cfg_dict["dropout"],
            activation=cfg_dict.get("activation", "gelu"),
            pooling=cfg_dict.get("pooling") or cfg_dict.get("pool", "mean"),
            head_hidden_size=cfg_dict["head_hidden_size"],
        )
        model_cfg = EncDecModelConfig(name="encoder_decoder_transformer", transformer=transformer_cfg)

        net = EncoderDecoderTransformerModel(
            input_dim=bundle["input_dim"],
            horizon=bundle["horizon"],
            input_kind=bundle["input_kind"],
            model_config=model_cfg,
        ).to(self._device)
        net.load_state_dict(bundle["model_state_dict"])
        net.eval()

        last_window: dict[str, list[tuple[int, float]]] = bundle["last_window"]
        X = _build_feature_matrix(last_window)  # (INPUT_LEN, 22)

        fs = bundle["feature_scaler"]
        X_scaled = fs.transform(X) if fs is not None else X

        tensor = torch.from_numpy(X_scaled).unsqueeze(0).to(self._device)  # (1, INPUT_LEN, 22)
        with torch.no_grad():
            out = net(tensor).squeeze(0).cpu().numpy()  # (HORIZON,)

        ts_scaler = bundle["target_scaler"]
        if ts_scaler is not None:
            out = ts_scaler.inverse_transform(out.reshape(1, -1))[0]

        price_data = sorted(last_window["Price"], key=lambda p: p[0])
        last_ts = price_data[-1][0]
        freq_ms = _freq_to_ms(self.config.forecast_frequency)

        datapoints = [
            AssetDatapoint(x=last_ts + (i + 1) * freq_ms, y=float(v))
            for i, v in enumerate(out)
        ]
        return ForecastResult(
            asset_id=self.config.target.asset_id,
            attribute_name=self.config.target.attribute_name,
            datapoints=datapoints,
        )


def _build_feature_matrix(last_window: dict[str, list[tuple[int, float]]]) -> np.ndarray:
    """Assemble (INPUT_LEN, 22) feature matrix in FEATURE_COLS order."""
    price_data = sorted(last_window.get("Price", []), key=lambda p: p[0])
    n = min(len(price_data), INPUT_LEN)
    if n == 0:
        raise ValueError("No Price data in bundle — model sync must run before forecasting")

    price_data = price_data[-INPUT_LEN:]
    timestamps_ms = np.array([p[0] for p in price_data], dtype=np.int64)

    result = np.zeros((INPUT_LEN, len(FEATURE_COLS)), dtype=np.float32)
    pad = INPUT_LEN - n  # zero-pad at start when fewer than INPUT_LEN points

    for col_idx, col_name in enumerate(FEATURE_COLS):
        if col_name in _TIME_FEATURE_COLS:
            computed = _compute_time_feature(col_name, timestamps_ms)
            result[pad:, col_idx] = computed
        else:
            series_data = sorted(last_window.get(col_name, []), key=lambda p: p[0])
            if not series_data:
                continue
            data_ts = np.array([p[0] for p in series_data], dtype=np.int64)
            data_vals = np.array([p[1] for p in series_data], dtype=np.float32)
            # Nearest past-or-equal lookup for each reference timestamp
            indices = np.searchsorted(data_ts, timestamps_ms, side="right") - 1
            indices = np.clip(indices, 0, len(data_vals) - 1)
            result[pad:, col_idx] = data_vals[indices]

    return result


def _compute_time_feature(col_name: str, timestamps_ms: np.ndarray) -> np.ndarray:
    dts = [datetime.fromtimestamp(int(ts) / 1000) for ts in timestamps_ms]
    if col_name == "day":
        return np.array([dt.day for dt in dts], dtype=np.float32)
    if col_name == "hour_sin":
        h = np.array([dt.hour for dt in dts], dtype=np.float32)
        return np.sin(2 * np.pi * h / 24)
    if col_name == "hour_cos":
        h = np.array([dt.hour for dt in dts], dtype=np.float32)
        return np.cos(2 * np.pi * h / 24)
    if col_name == "day_of_week_sin":
        d = np.array([dt.weekday() for dt in dts], dtype=np.float32)
        return np.sin(2 * np.pi * d / 7)
    if col_name == "day_of_week_cos":
        d = np.array([dt.weekday() for dt in dts], dtype=np.float32)
        return np.cos(2 * np.pi * d / 7)
    if col_name == "month_sin":
        m = np.array([dt.month for dt in dts], dtype=np.float32)
        return np.sin(2 * np.pi * m / 12)
    if col_name == "month_cos":
        m = np.array([dt.month for dt in dts], dtype=np.float32)
        return np.cos(2 * np.pi * m / 12)
    if col_name == "quarter_sin":
        q = np.array([(dt.month - 1) // 3 + 1 for dt in dts], dtype=np.float32)
        return np.sin(2 * np.pi * q / 4)
    if col_name == "quarter_cos":
        q = np.array([(dt.month - 1) // 3 + 1 for dt in dts], dtype=np.float32)
        return np.cos(2 * np.pi * q / 4)
    if col_name == "weekend_sin":
        w = np.array([1.0 if dt.weekday() >= 5 else 0.0 for dt in dts], dtype=np.float32)
        return np.sin(np.pi * w)
    if col_name == "weekend_cos":
        w = np.array([1.0 if dt.weekday() >= 5 else 0.0 for dt in dts], dtype=np.float32)
        return np.cos(np.pi * w)
    raise ValueError(f"Unknown time feature: {col_name}")


def _freq_to_ms(frequency: str) -> int:
    offset = pd.tseries.frequencies.to_offset(frequency)
    if offset is None:
        raise ValueError(f"Unrecognised forecast_frequency: {frequency!r}")
    nanos: int = int(pd.Timedelta(offset).value)  # type: ignore[arg-type]
    return nanos // 1_000_000
