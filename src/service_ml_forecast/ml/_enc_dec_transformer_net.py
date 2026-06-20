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

# Vendored from Nazim112/nl-energy-forecaster (originally CitrusBoy/exp2c-energy-forecaster).
# Kept local to avoid a hard dependency on the HF repo's src/ layout at runtime.

from __future__ import annotations

import math
from dataclasses import dataclass, field

import torch
import torch.nn as nn


@dataclass
class TransformerConfig:
    d_model: int = 256
    nhead: int = 8
    num_layers: int = 4
    num_decoder_layers: int | None = None
    dim_feedforward: int = 1024
    dropout: float = 0.1
    activation: str = "gelu"
    pooling: str = "mean"
    head_hidden_size: int = 128


@dataclass
class EncDecModelConfig:
    name: str = "encoder_decoder_transformer"
    transformer: TransformerConfig | None = field(default=None)


class SinusoidalPositionalEncoding(nn.Module):
    def __init__(self, d_model: int, dropout: float = 0.1, max_len: int = 5000) -> None:
        super().__init__()
        self.dropout = nn.Dropout(p=dropout)
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len).unsqueeze(1).float()
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        self.register_buffer("pe", pe.unsqueeze(0))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x + self.pe[:, : x.size(1)]  # type: ignore[index]
        return self.dropout(x)


class EncoderDecoderTransformerModel(nn.Module):
    """Encoder consumes lookback; learned query tokens cross-attend to encoder memory → MLP head."""

    def __init__(
        self,
        input_dim: int,
        horizon: int,
        input_kind: str,
        model_config: EncDecModelConfig,
    ) -> None:
        super().__init__()
        if model_config.transformer is None:
            raise ValueError("Transformer configuration required.")

        cfg = model_config.transformer
        num_dec = cfg.num_decoder_layers if cfg.num_decoder_layers is not None else cfg.num_layers

        self.input_proj = nn.Linear(input_dim, cfg.d_model)
        self.pos_enc = SinusoidalPositionalEncoding(cfg.d_model, dropout=cfg.dropout)

        encoder_layer = nn.TransformerEncoderLayer(
            d_model=cfg.d_model,
            nhead=cfg.nhead,
            dim_feedforward=cfg.dim_feedforward,
            dropout=cfg.dropout,
            batch_first=True,
            norm_first=True,
        )
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=cfg.num_layers)

        decoder_layer = nn.TransformerDecoderLayer(
            d_model=cfg.d_model,
            nhead=cfg.nhead,
            dim_feedforward=cfg.dim_feedforward,
            dropout=cfg.dropout,
            batch_first=True,
            norm_first=True,
        )
        self.decoder = nn.TransformerDecoder(decoder_layer, num_layers=num_dec)

        self.query_tokens = nn.Parameter(torch.randn(1, horizon, cfg.d_model))

        self.head = nn.Sequential(
            nn.Linear(cfg.d_model, cfg.head_hidden_size),
            nn.ReLU(),
            nn.Dropout(cfg.dropout),
            nn.Linear(cfg.head_hidden_size, 1),
        )

    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        B = inputs.size(0)
        memory = self.encoder(self.pos_enc(self.input_proj(inputs)))
        queries = self.query_tokens.expand(B, -1, -1)
        out = self.decoder(tgt=queries, memory=memory)
        return self.head(out).squeeze(-1)  # (B, horizon)
