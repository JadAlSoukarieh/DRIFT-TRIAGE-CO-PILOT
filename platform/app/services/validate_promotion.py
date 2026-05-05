# platform/app/services/validate_promotion.py
"""Promotion gate — programmatic checklist before accepting a promote request.

Day-4 checklist assertions:
1. model_uri exists in MLflow registry
2. Model metrics meet minimum bar (recall >= 0.75 on reference set)
3. No newer drift event has arrived since the investigation was opened
4. The approving investigation_id matches an active HIL approval

Raises ValueError with descriptive message if any check fails.
Called by routers/registry.py.

TODO: Implement assert_promotion_checklist(model_uri, investigation_id) -> None.
"""
