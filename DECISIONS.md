# Decisions

## Platform decisions (Hadi)

### Model selection: HistGradientBoostingClassifier
Three models were compared via 5-fold stratified CV (60/20/20 split):
- LogisticRegression: AUC 0.7896 ± 0.0054
- RandomForest: AUC 0.7707 ± 0.0082
- **HistGradientBoosting: AUC 0.7956 ± 0.0027**

Chosen for:
1. Highest mean on 5/6 metrics across folds
2. Tightest standard deviations (most stable)
3. sklearn-native — zero extra dependencies
4. Fastest training time (0.2s per fold)

### Threshold rule: highest where recall >= 0.75
Per the Week 5 Day 2 rule:
```
precision_recall_curve(y_true, y_proba) → thresholds[recall[:-1] >= 0.75].max()
```
Per-fold thresholds averaged across 5-fold CV → operating threshold = 0.3493.
Applied to every prediction before returning 0/1.

### SHA256 for artifact hashing
Switched from MD5 to SHA256 on Jad's agent recommendation:
- `compute_dataset_sha256()` in `run_training.py` produces 64-char hex
- `model_card.json` key is `"sha256"` (not `"md5"`)
- Promotion gate validates `"sha256"` key in model_card

### Candidate alias pattern — never auto-promote
Training logs model with `aliases=["candidate"]`. Production is only set via `POST /registry/promote` after gate validation + HIL approval. No training run ever self-promotes to Production.

### MLflow tracking URI portability
Default: `http://mlflow:5000` (Docker service name). Override via `.env` to `http://localhost:5000` for local dev. Same pattern for all service-to-service URLs.

### Feature preprocessing decisions
- `duration` dropped — recorded after call, leaks target
- `pdays==999` flagged as `pdays_never_contacted` sentinel (999 = never previously contacted)
- `'unknown'` treated as real category, not missing data — informative signal
- Numeric features: StandardScaler. Categorical: OneHotEncoder(handle_unknown='ignore')
- ColumnTransformer fit only on train set — never on val or test

### Worker idempotency
Key format: `idempotency:{action}:{investigation_id}:{target}`. SETNX with 1h TTL. Prevents duplicate retrains from the same investigation.

### Promotion audit
Every successful promote writes to Postgres `promotion_audit` table. Fields: model_uri, investigation_id, approved_by, from_alias (candidate), to_alias (Production), timestamp. Gracefully skips if Postgres is unavailable.

### Rollback safety
Worker refuses rollback jobs without `approval_id`. Validated rollbacks push to DLQ with "not implemented" — requires manual registry intervention. This is intentional: Production rollback is the most dangerous operation and deserves a human in the loop.

## Agent decisions (Jad)
<!-- Fill in by Jad -->

## Infrastructure decisions (shared)
<!-- Fill in by Jad -->

## Open questions
- Webhook vs polling: [fill]
- LLM choice: [fill]
- Queue idempotency strategy: idempotency key via Redis SETNX (see worker section above)
- HIL stale-approval handling: [fill]
- Checkpoint store sync with registry: [fill]
