"""Drift detection unit tests — PSI, chi², severity classification."""

import numpy as np
import pytest
from app.services.compute_drift import classify_severity, compute_chi2, compute_psi


def test_compute_psi_identical():
    rng = np.random.default_rng(42)
    ref = rng.normal(0, 1, 2000)
    cur = rng.normal(0, 1, 2000)
    psi = compute_psi(ref, cur)
    assert psi < 0.05, f"PSI should be near zero for identical distributions, got {psi}"


def test_compute_psi_divergent():
    rng = np.random.default_rng(42)
    ref = rng.normal(0, 1, 2000)
    cur = rng.normal(2, 1, 2000)
    psi_same = compute_psi(ref, cur)
    psi_diff = compute_psi(ref, rng.normal(3, 0.5, 2000))
    assert psi_same > 0.05, f"shifted distribution should show drift, got {psi_same}"
    assert psi_diff > psi_same, "larger shift should produce higher PSI"


def test_compute_psi_single_bin_boundary():
    ref = np.array([0.0] * 100)
    cur = np.array([0.0] * 100)
    psi = compute_psi(ref, cur, bins=5)
    assert psi < 0.01, f"empty bins should not explode PSI, got {psi}"


def test_compute_chi2_identical():
    ref = np.array(["a"] * 100 + ["b"] * 100 + ["c"] * 100)
    cur = np.array(["a"] * 100 + ["b"] * 100 + ["c"] * 100)
    chi2 = compute_chi2(ref, cur)
    assert chi2 < 0.5, f"identical categoricals should have chi² ≈ 0, got {chi2}"


def test_compute_chi2_divergent():
    ref = np.array(["a"] * 150 + ["b"] * 150)
    cur = np.array(["a"] * 200 + ["b"] * 100)
    chi2 = compute_chi2(ref, cur)
    assert chi2 > 1.0, f"divergent categoricals should have chi² > 0, got {chi2}"


def test_classify_severity_stable():
    assert classify_severity(0.05, 0.01, 0.08) == "stable"


def test_classify_severity_moderate():
    assert classify_severity(0.12, 0.08, 0.15) == "moderate"


def test_classify_severity_critical():
    assert classify_severity(0.26, 0.01, 0.02) == "critical"


def test_classify_severity_mixed():
    assert classify_severity(0.05, 0.30, 0.02) == "critical"
    assert classify_severity(0.05, 0.12, 0.02) == "moderate"
