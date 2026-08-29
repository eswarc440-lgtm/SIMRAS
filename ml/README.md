# SIMRAS Stage 5 ML

This package contains two deliberately separate training paths:

- `simras_ml.train` preserves the existing experimental SIMRAS asset-state
  health/risk trainer and its feature contract.
- `simras_ml.cli` runs the governed **research-transfer bridge deterioration
  pipeline** from annual U.S. FHWA National Bridge Inventory downloads.

The NBI pipeline never marks its resulting model as locally validated for Andhra
Pradesh. Keeping the training paths separate prevents the U.S. bridge model from
silently replacing the project-specific experimental pipeline.

The training job enforces bridge-level holdout splits, probability calibration,
metrics, data-volume gates, model manifests and checksums. Failed gates produce a
`REJECTED` manifest. Dams and barrages are intentionally outside this model's scope.

Example commands are documented in `STAGE5_ML_RUNBOOK.md` at the repository root.

The original asset-state trainer remains available with:

```bash
python -m simras_ml.train --task health --data training.csv --output artifacts/models
```
