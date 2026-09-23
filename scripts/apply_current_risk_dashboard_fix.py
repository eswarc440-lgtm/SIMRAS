from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if new in text:
        print(f"SKIP already patched: {path.relative_to(ROOT)}")
        return
    if old not in text:
        raise SystemExit(f"Expected patch anchor not found in {path}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"PATCHED: {path.relative_to(ROOT)}")


def main() -> None:
    twin = ROOT / "backend/app/services/twin_service.py"
    app = ROOT / "frontend/src/App.tsx"

    replace_once(
        twin,
        "from app.services.dam_hydrology_risk import score_dam_barrage_operational_risk\n",
        "from app.services.dam_hydrology_risk import score_dam_barrage_operational_risk\n"
        "from app.services.current_risk_service import (\n"
        "    load_latest_environment,\n"
        "    resolve_current_risk_snapshot,\n"
        ")\n",
    )

    replace_once(
        twin,
        '''    risk = predictions.get("risk")\n    model = await _active_asset_model(\n        session=session,\n        asset_id=asset.id,\n    )\n    quality = twin_quality_metadata(model, asset.asset_type)\n\n    return {\n''',
        '''    risk = predictions.get("risk")\n    model = await _active_asset_model(\n        session=session,\n        asset_id=asset.id,\n    )\n    quality = twin_quality_metadata(model, asset.asset_type)\n\n    environment: dict[str, dict[str, Any]] = {}\n    if str(asset.asset_type or "").lower() in {"dam", "barrage"}:\n        environment = await load_latest_environment(\n            session=session,\n            asset_id=asset.id,\n        )\n\n    current_risk = resolve_current_risk_snapshot(\n        asset_type=asset.asset_type,\n        persisted_risk=risk,\n        environment=environment,\n        dimensions=(\n            model.dimensions\n            if model is not None and model.dimensions\n            else {}\n        ),\n    )\n\n    return {\n''',
    )

    replace_once(
        twin,
        '''        "risk_score": (\n            risk.value\n            if risk is not None\n            else None\n        ),\n\n        "risk_level": (\n            risk.predicted_class\n            if risk is not None\n            else None\n        ),\n''',
        '''        "risk_score": current_risk["risk_score"],\n\n        "risk_level": current_risk["risk_level"],\n''',
    )

    replace_once(
        app,
        '''  const highRisk = assets.filter(\n    (asset) => asset.risk_level === "HIGH",\n  ).length;\n''',
        '''  const highRisk = assets.filter((asset) =>\n    ["HIGH", "CRITICAL"].includes(\n      (asset.risk_level ?? "").toUpperCase(),\n    ),\n  ).length;\n''',
    )

    replace_once(
        app,
        '            detail="Existing registry classification"\n',
        '            detail="Latest decision-support assessment"\n',
    )

    print("Current-risk dashboard integration patch complete.")


if __name__ == "__main__":
    main()
