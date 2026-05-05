"""Training pipeline — importable by worker and callable standalone.

Ported from initial-training notebook.
Called by worker/consume_queue.py on retrain jobs.

1. Load bank-additional-full.csv
2. Preprocess: drop duration, flag pdays sentinel, treat 'unknown' as category
3. Stratified 60/20/20 split
4. Fit ColumnTransformer + HistGradientBoostingClassifier pipeline
5. Tune threshold via 5-fold CV (recall >= min_recall)
6. Log to MLflow: binary, schema.json, model_card.json
7. Register as candidate alias (NOT Production)
8. Save model.joblib to data/

Returns: MLflow model_uri string.
"""

import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import joblib
import mlflow
import numpy as np
import pandas as pd
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from app.config.settings import Settings


NUMERIC_FEATURES = [
    "pdays_never_contacted",
    "age",
    "campaign",
    "pdays",
    "previous",
    "emp.var.rate",
    "cons.price.idx",
    "cons.conf.idx",
    "euribor3m",
    "nr.employed",
]

CATEGORICAL_FEATURES = [
    "job",
    "marital",
    "education",
    "default",
    "housing",
    "loan",
    "contact",
    "month",
    "day_of_week",
    "poutcome",
]

TARGET = "y"
RANDOM = 42


def load_and_clean(csv_path: str) -> tuple[pd.DataFrame, np.ndarray]:
    df = pd.read_csv(csv_path, sep=";")
    y = (df[TARGET] == "yes").astype(int).values
    df.drop(columns=[TARGET, "duration"], inplace=True)
    df["pdays_never_contacted"] = (df["pdays"] == 999).astype(int)
    return df, y


def find_threshold(y_true: np.ndarray, y_proba: np.ndarray, min_recall: float = 0.75) -> float:
    precision, recall, thresholds = precision_recall_curve(y_true, y_proba)
    valid = recall[:-1] >= min_recall
    if valid.any():
        return float(thresholds[valid].max())
    return 0.5


def compute_dataset_hash(csv_path: str) -> str:
    return hashlib.md5(Path(csv_path).read_bytes()).hexdigest()


def run_training_pipeline(dataset_path: str | None = None) -> str:
    settings = Settings()
    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
    ds_path = dataset_path or settings.dataset_path

    df, y = load_and_clean(ds_path)
    print(f"Loaded {df.shape[0]} rows, {df.shape[1]} features. Positive: {y.mean():.2%}")

    X_trainval, X_test, y_trainval, y_test = train_test_split(
        df, y, test_size=0.20, stratify=y, random_state=RANDOM,
    )

    preprocessor = ColumnTransformer([
        ("num", StandardScaler(), NUMERIC_FEATURES),
        ("cat", OneHotEncoder(handle_unknown="ignore", drop=None, sparse_output=False),
         CATEGORICAL_FEATURES),
    ])

    classifier = HistGradientBoostingClassifier(
        class_weight="balanced",
        max_iter=200,
        max_depth=None,
        random_state=RANDOM,
    )

    pipeline = Pipeline([
        ("preprocessor", preprocessor),
        ("classifier", classifier),
    ])

    # 5-fold CV for threshold
    skf = StratifiedKFold(n_splits=settings.cv_folds, shuffle=True, random_state=RANDOM)
    thresholds: list[float] = []

    for train_idx, val_idx in skf.split(X_trainval, y_trainval):
        X_tr = X_trainval.iloc[train_idx]
        y_tr = y_trainval[train_idx]
        X_v = X_trainval.iloc[val_idx]
        y_v = y_trainval[val_idx]
        pp = ColumnTransformer([
            ("num", StandardScaler(), NUMERIC_FEATURES),
            ("cat", OneHotEncoder(handle_unknown="ignore", drop=None, sparse_output=False),
             CATEGORICAL_FEATURES),
        ])
        X_tr_t = pp.fit_transform(X_tr)
        X_v_t = pp.transform(X_v)
        est = HistGradientBoostingClassifier(
            class_weight="balanced", max_iter=200, max_depth=None, random_state=RANDOM,
        )
        est.fit(X_tr_t, y_tr)
        y_v_proba = est.predict_proba(X_v_t)[:, 1]
        t = find_threshold(y_v, y_v_proba, settings.min_recall)
        thresholds.append(t)

    operating_threshold = float(np.mean(thresholds))
    print(f"CV threshold (mean): {operating_threshold:.4f}")

    # Final fit on trainval
    pipeline.fit(X_trainval, y_trainval)

    # Blind test evaluation
    y_test_proba = pipeline.predict_proba(X_test)[:, 1]
    y_test_pred = (y_test_proba >= operating_threshold).astype(int)

    test_acc = accuracy_score(y_test, y_test_pred)
    test_prec = precision_score(y_test, y_test_pred)
    test_rec = recall_score(y_test, y_test_pred)
    test_f1 = f1_score(y_test, y_test_pred)
    test_auc = roc_auc_score(y_test, y_test_proba)

    print(f"Test — Acc: {test_acc:.4f}  Prec: {test_prec:.4f}  Rec: {test_rec:.4f}  F1: {test_f1:.4f}  AUC: {test_auc:.4f}")

    # MLflow logging
    mlflow.set_experiment("bank_marketing_initial_training")

    with mlflow.start_run(run_name=f"Retrain_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}") as run:
        run_id = run.info.run_id

        mlflow.log_param("classifier", "HistGradientBoostingClassifier")
        mlflow.log_param("class_weight", "balanced")
        mlflow.log_param("max_iter", 200)
        mlflow.log_param("cv_folds", settings.cv_folds)
        mlflow.log_param("min_recall", settings.min_recall)

        mlflow.log_metric("test_accuracy", test_acc)
        mlflow.log_metric("test_precision", test_prec)
        mlflow.log_metric("test_recall", test_rec)
        mlflow.log_metric("test_f1", test_f1)
        mlflow.log_metric("test_roc_auc", test_auc)
        mlflow.log_metric("operating_threshold", operating_threshold)

        # Schema
        schema = {
            "numeric_features": NUMERIC_FEATURES,
            "categorical_features": CATEGORICAL_FEATURES,
            "target": {"name": TARGET, "classes": ["no", "yes"], "encoding": {"no": 0, "yes": 1}},
            "preprocessing": {
                "numeric": "StandardScaler",
                "categorical": "OneHotEncoder(handle_unknown='ignore', drop=None)",
            },
            "pipeline_steps": ["preprocessor", "classifier"],
            "classifier": "HistGradientBoostingClassifier",
            "hyperparameters": {
                "class_weight": "balanced",
                "max_iter": 200,
                "max_depth": None,
                "random_state": RANDOM,
            },
        }
        mlflow.log_dict(schema, "schema.json")

        # Model card
        dataset_hash = compute_dataset_hash(ds_path)
        model_card = {
            "model_name": "HistGradientBoostingClassifier",
            "training_timestamp": datetime.now(timezone.utc).isoformat(),
            "dataset": {
                "source": str(ds_path),
                "md5": dataset_hash,
                "rows": len(df),
                "features": len(NUMERIC_FEATURES) + len(CATEGORICAL_FEATURES),
                "positive_class_ratio": round(float(y.mean()), 4),
            },
            "trainval_split": {
                "trainval_ratio": 0.80,
                "test_ratio": 0.20,
                "random_state": RANDOM,
                "stratified": True,
            },
            "cv_folds": settings.cv_folds,
            "operating_threshold": round(operating_threshold, 4),
            "threshold_rule": "highest threshold where recall >= min_recall (per-fold, averaged)",
            "final_test_metrics": {
                "accuracy": round(test_acc, 4),
                "precision": round(test_prec, 4),
                "recall": round(test_rec, 4),
                "f1": round(test_f1, 4),
                "roc_auc": round(test_auc, 4),
            },
            "environment": {
                "python_version": sys.version.split()[0],
                "sklearn_version": sklearn.__version__,
                "pandas_version": pd.__version__,
                "mlflow_version": mlflow.__version__,
            },
        }
        mlflow.log_dict(model_card, "model_card.json")

        # Log model binary — register as candidate, NOT Production
        model_info = mlflow.sklearn.log_model(
            sk_model=pipeline,
            artifact_path="model",
            registered_model_name="bank_marketing_pipeline",
        )

        # Set alias to candidate only — never Production automatically
        client = mlflow.MlflowClient()
        try:
            client.set_registered_model_alias(
                name="bank_marketing_pipeline",
                alias="candidate",
                version=model_info.registered_model_version,
            )
        except Exception as exc:
            print(f"Warning: could not set candidate alias: {exc}")

        model_uri = f"models:/bank_marketing_pipeline@candidate"
        print(f"\nMLflow run: {run_id}")
        print(f"Model URI: {model_uri}")
        print(f"Artifacts: model/  schema.json  model_card.json")

    # Save to disk
    joblib_path = Path(settings.model_path)
    joblib_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, joblib_path)
    print(f"Model saved to {joblib_path.resolve()}")

    return model_uri


if __name__ == "__main__":
    uri = run_training_pipeline()
    print(f"\nTraining complete. URI: {uri}")
