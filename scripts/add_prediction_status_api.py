from pathlib import Path

path = Path("backend/app/api/routes/records.py")

if not path.exists():
    raise SystemExit(f"Missing file: {path}")

text = path.read_text(encoding="utf-8-sig")

marker = '@router.get("/assets/{asset_code}/predictions/history")'

if '"/assets/{asset_code}/predictions/status"' in text:
    print("Prediction status endpoint already exists.")
    raise SystemExit(0)

if marker not in text:
    raise SystemExit("Prediction history marker not found.")

endpoint = '''
@router.get("/assets/{asset_code}/predictions/status")
async def prediction_status(
    asset_code: str,
    session: AsyncSession = Depends(get_db),
) -> dict:
    """
    Return governed AI availability without running
    or persisting a prediction.
    """

    asset = await _asset(session, asset_code)

    if str(asset.asset_type or "").lower() == "bridge":
        from app.services.model_governance import (
            bridge_prediction_gate,
        )

        gate = await bridge_prediction_gate(
            session=session,
            asset=asset,
        )

        return {
            "asset": {
                "id": asset.id,
                "asset_code": asset.asset_code,
                "name": asset.name,
                "asset_type": asset.asset_type,
                "identity_status": asset.identity_status,
            },
            "prediction_available": bool(
                gate["allowed"]
            ),
            "status": (
                "AVAILABLE"
                if gate["allowed"]
                else "WITHHELD"
            ),
            "reason_code": gate["reason_code"],
            "model": gate.get("model"),
            "governance": gate.get(
                "governance",
                {},
            ),
        }

    return {
        "asset": {
            "id": asset.id,
            "asset_code": asset.asset_code,
            "name": asset.name,
            "asset_type": asset.asset_type,
            "identity_status": asset.identity_status,
        },
        "prediction_available": True,
        "status": "DECISION_SUPPORT_AVAILABLE",
        "reason_code": "NON_BRIDGE_MULTIFACTOR_SCOPE",
        "model": {
            "model_name": "simras_multifactor_health",
            "stage": "DECISION_SUPPORT",
            "model_validated": False,
        },
        "governance": {
            "warning": (
                "Transparent multifactor decision support; "
                "not a locally validated structural model."
            )
        },
    }


'''

text = text.replace(
    marker,
    endpoint + marker,
    1,
)

path.write_text(
    text,
    encoding="utf-8",
)

print("Prediction status API added successfully.")
