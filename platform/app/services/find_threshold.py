"""Operating threshold via precision-recall trade-off.

Week 5 Day 2 rule: highest threshold where recall >= min_recall.
Ported from initial-training notebook.
"""

import numpy as np
from sklearn.metrics import precision_recall_curve


def find_threshold(
    y_true: np.ndarray,
    y_proba: np.ndarray,
    min_recall: float = 0.75,
) -> float:
    precision, recall, thresholds = precision_recall_curve(y_true, y_proba)
    valid = recall[:-1] >= min_recall
    if valid.any():
        return float(thresholds[valid].max())
    return 0.5
