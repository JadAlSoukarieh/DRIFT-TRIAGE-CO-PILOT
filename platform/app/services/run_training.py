# platform/app/services/run_training.py
"""Training pipeline — importable by worker/handlers.

Ported from initial-training notebook.
Called by worker/consume_queue.py on retrain jobs.

1. Load bank-additional-full.csv
2. Preprocess: drop duration, flag pdays sentinel, treat 'unknown' as category
3. Stratified 60/20/20 split
4. Fit ColumnTransformer + HistGradientBoostingClassifier pipeline
5. Tune threshold via 5-fold CV (recall >= 0.75)
6. Log to MLflow: binary artifact, schema.json, model_card.json
7. Save model.joblib to data/

Returns: MLflow model_uri string.

TODO: Implement run_training_pipeline() -> str.
"""
