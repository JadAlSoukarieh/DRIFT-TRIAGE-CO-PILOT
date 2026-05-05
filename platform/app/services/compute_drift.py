# platform/app/services/compute_drift.py
"""Drift computation — PSI on numerics, chi² on categoricals.

- Compute PSI (Population Stability Index) over a rolling window of recent predictions
  using reference statistics loaded from reference_stats.json or computed from training set
- Compute chi² test of independence for each categorical feature
  comparing reference distribution against recent window
- Compute output-distribution drift (Kolmogorov-Smirnov or simple ratio change)
- Combine scores into a severity classification (stable / moderate / critical)

TODO: Implement compute_psi(), compute_chi2(), classify_severity().
"""
