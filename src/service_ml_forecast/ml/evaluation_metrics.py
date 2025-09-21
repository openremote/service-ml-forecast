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
