"""Drift computation — PSI on numerics, chi² on categoricals.

PSI (Population Stability Index): compares two distributions bin-by-bin.
chi²: test of independence for categorical feature distributions.
output_drift: fraction of positive predictions changed vs reference.

Severity thresholds:
- psi/chi² > critical   → severity = "critical"
- psi/chi² > moderate   → severity = "moderate"
- otherwise             → severity = "stable"
"""

import numpy as np
from scipy.stats import chi2_contingency


def compute_psi(reference: np.ndarray, current: np.ndarray, bins: int = 10) -> float:
    ref_counts, edges = np.histogram(reference, bins=bins)
    cur_counts, _ = np.histogram(current, bins=edges)
    ref_counts = ref_counts.astype(np.float64)
    cur_counts = cur_counts.astype(np.float64)
    epsilon = 1e-10
    ref_props = (ref_counts + epsilon) / (ref_counts.sum() + epsilon * bins)
    cur_props = (cur_counts + epsilon) / (cur_counts.sum() + epsilon * bins)
    psi = np.sum((ref_props - cur_props) * np.log((ref_props + epsilon) / (cur_props + epsilon)))
    return float(psi)


def compute_chi2(
    reference: np.ndarray,
    current: np.ndarray,
) -> float:
    ref_cats = np.unique(reference)
    cur_cats = np.unique(current)
    all_cats = np.union1d(ref_cats, cur_cats)
    ref_counts = np.array([np.sum(reference == c) for c in all_cats])
    cur_counts = np.array([np.sum(current == c) for c in all_cats])
    table = np.array([ref_counts, cur_counts])
    chi2, p, _, _ = chi2_contingency(table)
    return float(chi2)


def classify_severity(
    max_psi: float,
    max_chi2: float,
    output_drift: float,
    moderate: float = 0.10,
    critical: float = 0.25,
) -> str:
    worst = max(max_psi, max_chi2, output_drift)
    if worst >= critical:
        return "critical"
    if worst >= moderate:
        return "moderate"
    return "stable"
