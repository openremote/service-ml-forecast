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

from dataclasses import dataclass


@dataclass
class EvaluationMetrics:
    """
    General evaluation metrics for a model.

    RMSE: Root Mean Squared Error - measures typical forecast error in same units as data.
           Higher values indicate larger prediction errors. Penalizes outliers heavily.

    MAE: Mean Absolute Error - measures average absolute difference between predicted and actual values.
          More robust to outliers than RMSE. Same units as data.

    MAPE: Mean Absolute Percentage Error - measures average percentage error relative to actual values.
           Expressed as decimal (0.05 = 5% error). Can be misleading when actual values are near zero.

    R2: R-squared (coefficient of determination) - measures proportion of variance explained by the model.
         Range: 0-1 (1.0 = perfect, 0.0 = no better than mean, negative = worse than mean).
    """

    rmse: float
    mae: float
    mape: float
    r2: float
