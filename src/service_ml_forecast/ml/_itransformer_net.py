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

import torch
import torch.nn as nn


class ITransformerEncoderLayer(nn.Module):
    def __init__(self, d_model: int, n_heads: int, d_ff: int, dropout: float) -> None:
        super().__init__()
        self.attn = nn.MultiheadAttention(d_model, n_heads, dropout=dropout, batch_first=True)
        self.ff = nn.Sequential(
            nn.Linear(d_model, d_ff),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(d_ff, d_model),
        )
        self.norm1 = nn.LayerNorm(d_model)
        self.norm2 = nn.LayerNorm(d_model)
        self.drop = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        residual = x
        x = self.norm1(x)
        x, _ = self.attn(x, x, x)
        x = residual + self.drop(x)

        residual = x
        x = self.norm2(x)
        x = self.ff(x)
        x = residual + self.drop(x)
        return x


class ITransformerNet(nn.Module):
    """Inverted Transformer for multivariate time series forecasting.

    Each variate's full time series becomes a token; attention is computed over variates.
    Paper: https://arxiv.org/abs/2310.06625
    """

    N_VARS = 6  # tariff_norm, hour_sin, hour_cos, dow_sin, dow_cos, is_weekend
    TARGET_VAR_IDX = 0

    def __init__(
        self,
        seq_len: int,
        pred_len: int,
        d_model: int = 128,
        n_heads: int = 4,
        n_layers: int = 2,
        d_ff: int = 256,
        dropout: float = 0.1,
    ) -> None:
        super().__init__()
        self.seq_len = seq_len
        self.pred_len = pred_len

        self.embed = nn.Linear(seq_len, d_model)
        self.encoder = nn.Sequential(
            *[ITransformerEncoderLayer(d_model, n_heads, d_ff, dropout) for _ in range(n_layers)]
        )
        self.norm = nn.LayerNorm(d_model)
        self.projection = nn.Linear(d_model, pred_len)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: [batch, seq_len, n_vars]
        x = x.permute(0, 2, 1)           # [batch, n_vars, seq_len]
        x = self.embed(x)                 # [batch, n_vars, d_model]
        x = self.encoder(x)               # [batch, n_vars, d_model]
        x = self.norm(x)                  # [batch, n_vars, d_model]
        x = self.projection(x)            # [batch, n_vars, pred_len]
        return x[:, self.TARGET_VAR_IDX, :]  # [batch, pred_len]
