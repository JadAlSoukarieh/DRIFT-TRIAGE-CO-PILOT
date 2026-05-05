# platform/tests/test_drift.py
"""Drift detection unit tests.

1. test_compute_psi_identical — PSI(identical distributions) ≈ 0
2. test_compute_psi_divergent — PSI(shifted distributions) > threshold
3. test_compute_chi2 — chi² returns valid p-values per categorical feature

TODO: Implement all tests with synthetic distributions.
"""
