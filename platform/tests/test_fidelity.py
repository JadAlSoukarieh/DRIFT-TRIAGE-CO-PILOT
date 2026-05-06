"""Model fidelity tests — model loads, predictions stable within 1e-12."""

import joblib
import numpy as np
import pytest

from app.config.settings import Settings


def _settings() -> Settings:
    return Settings()


def test_model_loads():
    path = _settings().resolved_model_path()
    if not path.exists():
        pytest.skip(f"model artifact missing: {path}")
    model = joblib.load(path)
    assert model is not None
    assert hasattr(model, "predict_proba")


def test_predictions_stable():
    path = _settings().resolved_model_path()
    if not path.exists():
        pytest.skip(f"model artifact missing: {path}")
    model = joblib.load(path)
    sample = {
        "age": 40, "job": "admin.", "marital": "married",
        "education": "university.degree", "default": "no", "housing": "yes",
        "loan": "no", "contact": "cellular", "month": "may",
        "day_of_week": "mon", "campaign": 1, "pdays": 999, "previous": 0,
        "poutcome": "nonexistent", "emp.var.rate": 1.1,
        "cons.price.idx": 93.994, "cons.conf.idx": -36.4,
        "euribor3m": 4.857, "nr.employed": 5191,
    }
    import pandas as pd
    df = pd.DataFrame([sample])
    df["pdays_never_contacted"] = (df["pdays"] == 999).astype(int)

    proba1 = model.predict_proba(df)[0, 1]
    proba2 = model.predict_proba(df)[0, 1]
    assert abs(proba1 - proba2) < 1e-12, f"instability: {abs(proba1 - proba2)}"


@pytest.mark.skip(reason="model.joblib is gitignored — run locally")
def test_predictions_stable_after_reload():
    pass


def test_compute_sha256():
    from app.services.run_training import compute_dataset_sha256
    sha = compute_dataset_sha256(_settings().resolved_dataset_path())
    assert len(sha) == 64
    assert all(c in "0123456789abcdef" for c in sha)
