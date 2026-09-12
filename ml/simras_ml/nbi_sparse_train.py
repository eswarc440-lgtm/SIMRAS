from __future__ import annotations
import argparse, hashlib, json
from datetime import UTC, datetime
from pathlib import Path
import joblib, numpy as np, pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, mean_absolute_error, mean_squared_error, roc_auc_score
from sklearn.pipeline import Pipeline
from simras_ml.nbi import add_targets, stable_partition

FEATURES = ["age_years","material_code","span_count","max_span_m","structure_length_m"]

def split(frame):
    p = frame["bridge_key"].map(stable_partition)
    return frame[p < 70].copy(), frame[(p >= 70) & (p < 85)].copy(), frame[p >= 85].copy()

def pipe(model):
    return Pipeline([("imputer", SimpleImputer(strategy="median", add_indicator=True)), ("model", model)])

def logit(prob):
    prob = np.clip(prob, 1e-6, 1 - 1e-6)
    return np.log(prob / (1 - prob)).reshape(-1, 1)

def ece(y, prob, bins=10):
    edges = np.linspace(0, 1, bins + 1); total = 0.0
    for low, high in zip(edges[:-1], edges[1:], strict=True):
        mask = (prob >= low) & (prob <= high if high == 1 else prob < high)
        if mask.any():
            total += float(mask.mean()) * abs(float(y[mask].mean()) - float(prob[mask].mean()))
    return float(total)

def checksum(path):
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""): h.update(block)
    return h.hexdigest()

def coverage(frame):
    return {c: round(float(frame[c].notna().mean()), 6) for c in FEATURES}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", type=Path, required=True)
    ap.add_argument("--artifact-dir", type=Path, required=True)
    ap.add_argument("--horizon-years", type=int, default=3)
    a = ap.parse_args()

    panel = pd.read_csv(a.panel)
    missing = [c for c in ["bridge_key","report_year",*FEATURES] if c not in panel.columns]
    if missing: raise RuntimeError(f"NBI panel missing columns: {missing}")
    labelled = add_targets(panel, horizon_years=a.horizon_years)
    train, cal, test = split(labelled)

    if len(train) < 50000 or train.bridge_key.nunique() < 10000:
        raise RuntimeError("Training population too small for sparse challenger")
    if set(train.bridge_key) & set(test.bridge_key): raise RuntimeError("train/test bridge leakage")
    if set(train.bridge_key) & set(cal.bridge_key): raise RuntimeError("train/cal bridge leakage")
    if set(cal.bridge_key) & set(test.bridge_key): raise RuntimeError("cal/test bridge leakage")

    htr = train.dropna(subset=["next_condition_rating"]); hte = test.dropna(subset=["next_condition_rating"])
    rtr = train.dropna(subset=["poor_within_horizon"]); rca = cal.dropna(subset=["poor_within_horizon"]); rte = test.dropna(subset=["poor_within_horizon"])

    health = pipe(HistGradientBoostingRegressor(learning_rate=.055,max_iter=300,max_leaf_nodes=31,l2_regularization=1.0,random_state=440))
    risk = pipe(HistGradientBoostingClassifier(learning_rate=.05,max_iter=300,max_leaf_nodes=31,l2_regularization=1.0,random_state=440))
    health.fit(htr[FEATURES], htr["next_condition_rating"])
    risk.fit(rtr[FEATURES], rtr["poor_within_horizon"].astype(int))

    raw_cal = risk.predict_proba(rca[FEATURES])[:,1]
    calibrator = LogisticRegression(max_iter=1000).fit(logit(raw_cal), rca["poor_within_horizon"].astype(int))

    hp = health.predict(hte[FEATURES]); hy = hte["next_condition_rating"].to_numpy(float)
    raw = risk.predict_proba(rte[FEATURES])[:,1]; rp = calibrator.predict_proba(logit(raw))[:,1]; ry = rte["poor_within_horizon"].to_numpy(int)
    median_target = float(np.median(htr["next_condition_rating"])); baseline_hp = np.full(len(hy), median_target)
    prevalence = float(rtr["poor_within_horizon"].mean()); baseline_rp = np.full(len(ry), prevalence)
    metrics = {
      "health_mae_rating": float(mean_absolute_error(hy,hp)),
      "health_rmse_rating": float(mean_squared_error(hy,hp)**.5),
      "health_baseline_mae_rating": float(mean_absolute_error(hy,baseline_hp)),
      "risk_roc_auc": float(roc_auc_score(ry,rp)),
      "risk_pr_auc": float(average_precision_score(ry,rp)),
      "risk_brier": float(brier_score_loss(ry,rp)),
      "risk_ece": ece(ry,rp),
      "risk_prevalence": float(ry.mean()),
      "risk_baseline_brier": float(brier_score_loss(ry,baseline_rp)),
    }
    gates = {
      "health_beats_baseline": metrics["health_mae_rating"] < metrics["health_baseline_mae_rating"],
      "health_mae_le_1_25": metrics["health_mae_rating"] <= 1.25,
      "risk_auc_ge_0_70": metrics["risk_roc_auc"] >= .70,
      "risk_pr_auc_beats_prevalence": metrics["risk_pr_auc"] > metrics["risk_prevalence"],
      "risk_brier_beats_baseline": metrics["risk_brier"] < metrics["risk_baseline_brier"],
      "risk_ece_le_0_10": metrics["risk_ece"] <= .10,
    }
    stage = "RESEARCH_TRANSFER" if all(gates.values()) else "REJECTED"

    a.artifact_dir.mkdir(parents=True, exist_ok=True)
    checksums = {}
    for name, model in {"health.joblib":health,"risk.joblib":risk,"risk_calibrator.joblib":calibrator}.items():
        p=a.artifact_dir/name; joblib.dump(model,p); checksums[name]=checksum(p)
    err = hp-hy
    manifest = {
      "model_name":"simras_nbi_bridge_sparse_challenger",
      "version":datetime.now(UTC).strftime("nbi_sparse_%Y%m%d_%H%M%S"),
      "stage":stage,"model_validated":False,
      "training_scope":"FHWA_NBI_US_BRIDGES_SPARSE_RESEARCH_TRANSFER",
      "prediction_horizon_years":a.horizon_years,
      "feature_version":"nbi_bridge_sparse_state_v1","features":FEATURES,
      "training_rows":int(len(train)),"calibration_rows":int(len(cal)),"test_rows":int(len(test)),
      "training_bridges":int(train.bridge_key.nunique()),"calibration_bridges":int(cal.bridge_key.nunique()),"test_bridges":int(test.bridge_key.nunique()),
      "training_years":sorted(int(v) for v in labelled.report_year.dropna().unique()),
      "evaluation_protocol":{"split_unit":"bridge_key","train_partition":"<70","calibration_partition":"70-84","test_partition":">=85","bridge_identity_leakage_control":True,"test_partition_held_out":True,"calibration_uses_test":False},
      "feature_coverage_training":coverage(train),"feature_coverage_test":coverage(test),
      "health_error_quantiles_rating":{"lower":float(np.quantile(err,.10)),"upper":float(np.quantile(err,.90))},
      "metrics":metrics,"gates":gates,"artifact_checksums":checksums,
      "data_source":"U.S. FHWA National Bridge Inventory annual histories",
      "limitations":["Not locally validated for Andhra Pradesh","Sparse transfer model omits condition rating","Use only as research decision support","Dam and barrage predictions are outside scope","RUL intentionally not produced"],
      "created_at":datetime.now(UTC).isoformat(),
    }
    (a.artifact_dir/"manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    print(json.dumps(manifest,indent=2))
    return 0 if stage=="RESEARCH_TRANSFER" else 2

if __name__=="__main__": raise SystemExit(main())
