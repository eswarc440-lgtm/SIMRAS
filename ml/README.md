# SIMRAS ML pipeline

The web application uses `transparent_rules_v1` until a trained model passes the
dataset and evaluation gates. The training unit is one asset at one state time.
Repeated observations of an asset are never randomly split across train/test.

Required features are defined in `simras_ml/features.py`. Create a verified CSV
with real labels, then run:

```bash
python -m simras_ml.train --task health --data /data/training/asset_states.csv
python -m simras_ml.train --task risk --data /data/training/asset_states.csv
```

The trainer refuses datasets with fewer than 10 distinct assets, holds out
complete assets, writes an immutable model card/checksum and logs the run to
MLflow. A successful training run remains experimental until engineering and
calibration review changes its registry stage.

