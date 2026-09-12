from __future__ import annotations

from collections import Counter
from datetime import datetime
from io import BytesIO, StringIO
import csv
import html
import zipfile

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import desc, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.entities import Asset, Inspection, Maintenance, Prediction

router = APIRouter(tags=["ui-compat"])


def _value(obj, *names, default=None):
    for name in names:
        if hasattr(obj, name):
            value = getattr(obj, name)
            if value is not None:
                return value
    return default


def _iso(value):
    if value is None:
        return None
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


def _risk_level(score):
    if score is None:
        return "UNKNOWN"
    return "HIGH" if score >= 70 else "MEDIUM" if score >= 40 else "LOW"


async def _prediction_index(session: AsyncSession):
    rows = (await session.scalars(select(Prediction).order_by(desc(Prediction.prediction_time)))).all()
    index = {}
    for row in rows:
        key = (row.asset_id, str(row.target).lower())
        index.setdefault(key, row)
    return index


def _asset_payload(asset, predictions=None):
    predictions = predictions or {}
    health = predictions.get((asset.id, "health"))
    risk = predictions.get((asset.id, "risk"))
    rul = predictions.get((asset.id, "rul")) or predictions.get((asset.id, "remaining_life"))
    health_score = _value(health, "value")
    risk_score = _value(risk, "value")
    rul_value = _value(rul, "value")
    asset_code = str(_value(asset, "asset_code", default=asset.id))
    return {
        "id": asset_code,
        "asset_id": asset_code,
        "asset_code": asset_code,
        "name": _value(asset, "name", default=asset_code),
        "type": _value(asset, "asset_type", "type", default="other"),
        "asset_type": _value(asset, "asset_type", "type", default="other"),
        "district": _value(asset, "district", default="Unknown"),
        "location": _value(asset, "district", default="Unknown"),
        "latitude": _value(asset, "latitude", "lat"),
        "longitude": _value(asset, "longitude", "lng", "lon"),
        "lat": _value(asset, "latitude", "lat"),
        "lng": _value(asset, "longitude", "lng", "lon"),
        "built_year": _value(asset, "built_year"),
        "design_life": _value(asset, "design_life", "design_life_years"),
        "age": _value(asset, "current_age", "age"),
        "condition": _value(asset, "condition", default="UNKNOWN"),
        "owner": _value(asset, "owner", default="Unknown"),
        "material": _value(asset, "material", default="Unknown"),
        "identity_status": _value(asset, "identity_status", default="UNKNOWN"),
        "status": _value(asset, "status", default="Operational"),
        "health_score": health_score,
        "risk_score": risk_score,
        "risk_level": _value(risk, "predicted_class", default=_risk_level(risk_score)),
        "remaining_useful_life": rul_value,
        "prediction_time": _iso(_value(risk, "prediction_time") or _value(health, "prediction_time")),
        "prediction_confidence": _value(risk, "confidence_score") or _value(health, "confidence_score"),
    }


async def _find_asset(session: AsyncSession, identifier: str):
    stmt = select(Asset).where(Asset.asset_code == identifier)
    if identifier.isdigit():
        stmt = select(Asset).where(or_(Asset.asset_code == identifier, Asset.id == int(identifier)))
    asset = await session.scalar(stmt)
    if asset is None:
        raise HTTPException(status_code=404, detail=f"Asset {identifier} not found")
    return asset


@router.get("/infrastructure")
async def infrastructure_list(
    limit: int = Query(100, ge=1, le=5000),
    skip: int = Query(0, ge=0),
    asset_type: str | None = None,
    district: str | None = None,
    session: AsyncSession = Depends(get_db),
):
    stmt = select(Asset)
    count_stmt = select(func.count()).select_from(Asset)
    if asset_type:
        stmt = stmt.where(Asset.asset_type == asset_type)
        count_stmt = count_stmt.where(Asset.asset_type == asset_type)
    if district and hasattr(Asset, "district"):
        stmt = stmt.where(Asset.district == district)
        count_stmt = count_stmt.where(Asset.district == district)
    total = int(await session.scalar(count_stmt) or 0)
    assets = (await session.scalars(stmt.order_by(Asset.id).offset(skip).limit(limit))).all()
    predictions = await _prediction_index(session)
    return {"total": total, "limit": limit, "skip": skip, "items": [_asset_payload(a, predictions) for a in assets]}


@router.get("/infrastructure/summary")
async def infrastructure_summary(session: AsyncSession = Depends(get_db)):
    assets = (await session.scalars(select(Asset))).all()
    counts = Counter(str(_value(a, "asset_type", default="other")).lower() for a in assets)
    return {"total": len(assets), "by_type": dict(counts)}


@router.get("/infrastructure/{identifier}")
async def infrastructure_detail(identifier: str, session: AsyncSession = Depends(get_db)):
    asset = await _find_asset(session, identifier)
    predictions = await _prediction_index(session)
    return _asset_payload(asset, predictions)


@router.get("/gis/assets")
async def gis_assets(
    limit: int = Query(500, ge=1, le=5000),
    asset_type: str | None = None,
    session: AsyncSession = Depends(get_db),
):
    stmt = select(Asset)
    if asset_type:
        stmt = stmt.where(Asset.asset_type == asset_type)
    assets = (await session.scalars(stmt.order_by(Asset.id).limit(limit))).all()
    predictions = await _prediction_index(session)
    features = []
    for asset in assets:
        p = _asset_payload(asset, predictions)
        lat, lng = p.get("latitude"), p.get("longitude")
        if lat is None or lng is None:
            continue
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [float(lng), float(lat)]},
            "properties": p,
        })
    return {"type": "FeatureCollection", "features": features, "total": len(features)}


@router.get("/gis/assets/bbox")
async def gis_bbox(
    min_lat: float,
    min_lng: float,
    max_lat: float,
    max_lng: float,
    limit: int = Query(1000, ge=1, le=5000),
    session: AsyncSession = Depends(get_db),
):
    data = await gis_assets(limit=limit, asset_type=None, session=session)
    data["features"] = [f for f in data["features"] if min_lat <= f["geometry"]["coordinates"][1] <= max_lat and min_lng <= f["geometry"]["coordinates"][0] <= max_lng]
    data["total"] = len(data["features"])
    return data


@router.get("/gis/assets/{identifier}")
async def gis_asset(identifier: str, session: AsyncSession = Depends(get_db)):
    asset = await _find_asset(session, identifier)
    predictions = await _prediction_index(session)
    p = _asset_payload(asset, predictions)
    if p["latitude"] is None or p["longitude"] is None:
        raise HTTPException(status_code=404, detail="Asset coordinates unavailable")
    return {"type": "Feature", "geometry": {"type": "Point", "coordinates": [float(p["longitude"]), float(p["latitude"])]}, "properties": p}


@router.get("/inspections")
async def inspections(
    limit: int = Query(100, ge=1, le=1000),
    session: AsyncSession = Depends(get_db),
):
    rows = (
        await session.execute(
            select(
                Inspection,
                Asset.asset_code,
                Asset.name,
            )
            .join(
                Asset,
                Asset.id == Inspection.asset_id,
            )
            .order_by(
                desc(Inspection.inspection_date)
            )
            .limit(limit)
        )
    ).all()

    items = []

    for row, asset_code, asset_name in rows:
        score = _value(
            row,
            "score",
            "condition_score",
            "inspection_score",
        )

        items.append(
            {
                "id": row.id,
                "asset_code": asset_code,
                "asset_id": asset_code,
                "asset_name": asset_name,
                "inspection_type": _value(
                    row,
                    "inspection_type",
                    default="Inspection",
                ),
                "inspection_date": _iso(
                    _value(row, "inspection_date")
                ),
                "inspector": _value(
                    row,
                    "inspector",
                    "inspector_name",
                ),
                "inspection_score": score,
                "condition_score": score,
                "condition": _value(row, "condition"),
                "notes": _value(
                    row,
                    "findings",
                    "notes",
                    "remarks",
                ),
                "quality_flag": _value(
                    row,
                    "quality_flag",
                ),
                "is_synthetic": bool(
                    _value(
                        row,
                        "is_synthetic",
                        default=False,
                    )
                ),
                "source_id": _value(
                    row,
                    "source_id",
                ),
                "created_at": _iso(
                    _value(
                        row,
                        "created_at",
                        "inspection_date",
                    )
                ),
            }
        )

    return {
        "total": len(items),
        "items": items,
    }


@router.get("/maintenance")
async def maintenance(limit: int = Query(100, ge=1, le=1000), session: AsyncSession = Depends(get_db)):
    date_col = getattr(Maintenance, "maintenance_date", Maintenance.id)
    rows = (await session.execute(select(Maintenance, Asset.asset_code).join(Asset, Asset.id == Maintenance.asset_id).order_by(desc(date_col)).limit(limit))).all()
    items = []
    for row, asset_code in rows:
        items.append({
            "id": row.id,
            "asset_id": asset_code,
            "maintenance_type": _value(row, "maintenance_type", "action", default="Maintenance"),
            "description": _value(row, "description", "action"),
            "priority": _value(row, "priority"),
            "status": _value(row, "status", default="planned"),
            "cost": _value(row, "cost", "estimated_cost", "actual_cost"),
            "maintenance_date": _iso(_value(row, "maintenance_date")),
            "planned_start_date": _iso(_value(row, "planned_start_date", "maintenance_date")),
            "actual_completion_date": _iso(_value(row, "actual_completion_date")),
            "next_due": _iso(_value(row, "next_due")),
            "performed_by": _value(row, "performed_by", "assigned_contractor"),
            "created_at": _iso(_value(row, "created_at", "maintenance_date")),
        })
    return {"total": len(items), "items": items}


@router.get("/predictions")
async def predictions(limit: int = Query(100, ge=1, le=1000), session: AsyncSession = Depends(get_db)):
    rows = (await session.execute(select(Prediction, Asset.asset_code, Asset.name).join(Asset, Asset.id == Prediction.asset_id).order_by(desc(Prediction.prediction_time)).limit(limit))).all()
    items = [{
        "id": row.id,
        "asset_id": asset_code,
        "asset_name": asset_name,
        "target": row.target,
        "value": row.value,
        "predicted_class": row.predicted_class,
        "confidence": row.confidence_score,
        "confidence_score": row.confidence_score,
        "lower_bound": row.lower_bound,
        "upper_bound": row.upper_bound,
        "model_version": row.model_version,
        "feature_version": row.feature_version,
        "status": row.status,
        "prediction_time": _iso(row.prediction_time),
        "predicted_at": _iso(row.prediction_time),
        "factors": row.factors,
    } for row, asset_code, asset_name in rows]
    return {"total": len(items), "items": items, "predictions": items}


@router.get("/predictions/summary")
async def prediction_summary(session: AsyncSession = Depends(get_db)):
    count = int(await session.scalar(select(func.count()).select_from(Prediction)) or 0)
    latest = await session.scalar(select(func.max(Prediction.prediction_time)))
    return {"total_predictions": count, "latest_prediction": _iso(latest)}


@router.get("/predictions/high-risk")
async def high_risk_predictions(limit: int = Query(50, ge=1, le=500), session: AsyncSession = Depends(get_db)):
    rows = (await session.execute(select(Prediction, Asset.asset_code, Asset.name).join(Asset, Asset.id == Prediction.asset_id).where(Prediction.target == "risk", Prediction.value >= 70).order_by(desc(Prediction.value)).limit(limit))).all()
    return [{"id": row.id, "asset_id": code, "asset_name": name, "risk_score": row.value, "risk_level": row.predicted_class or _risk_level(row.value), "confidence_score": row.confidence_score, "prediction_time": _iso(row.prediction_time)} for row, code, name in rows]


@router.get("/predictions/{identifier}")
async def prediction_for_asset(identifier: str, session: AsyncSession = Depends(get_db)):
    asset = await _find_asset(session, identifier)
    rows = (await session.scalars(select(Prediction).where(Prediction.asset_id == asset.id).order_by(desc(Prediction.prediction_time)))).all()
    latest = {}
    for row in rows:
        latest.setdefault(str(row.target).lower(), row)
    risk = latest.get("risk")
    health = latest.get("health")
    rul = latest.get("rul") or latest.get("remaining_life")
    return {
        "asset_id": asset.asset_code,
        "health_score": _value(health, "value"),
        "risk_score": _value(risk, "value"),
        "risk_level": _value(risk, "predicted_class", default=_risk_level(_value(risk, "value"))),
        "remaining_useful_life": _value(rul, "value"),
        "confidence_score": _value(risk, "confidence_score") or _value(health, "confidence_score"),
        "model_version": _value(risk, "model_version") or _value(health, "model_version"),
        "prediction_time": _iso(_value(risk, "prediction_time") or _value(health, "prediction_time")),
        "status": _value(risk, "status") or _value(health, "status") or "UNAVAILABLE",
    }


@router.get("/dashboard/overview")
async def dashboard_overview(session: AsyncSession = Depends(get_db)):
    assets = (await session.scalars(select(Asset))).all()
    predictions = await _prediction_index(session)
    payloads = [_asset_payload(a, predictions) for a in assets]
    by_type = Counter(str(a.get("asset_type") or "other").lower() for a in payloads)
    districts = Counter(str(a.get("district") or "Unknown") for a in payloads)
    risk_scores = [float(a["risk_score"]) for a in payloads if a.get("risk_score") is not None]
    health_scores = [float(a["health_score"]) for a in payloads if a.get("health_score") is not None]
    rul_values = [float(a["remaining_useful_life"]) for a in payloads if a.get("remaining_useful_life") is not None]
    high = [a for a in payloads if a.get("risk_score") is not None and float(a["risk_score"]) >= 70]
    medium = [a for a in payloads if a.get("risk_score") is not None and 40 <= float(a["risk_score"]) < 70]
    low = [a for a in payloads if a.get("risk_score") is not None and float(a["risk_score"]) < 40]
    top = sorted([a for a in payloads if a.get("risk_score") is not None], key=lambda a: float(a["risk_score"]), reverse=True)[:10]
    recent = sorted([a for a in payloads if a.get("prediction_time")], key=lambda a: a["prediction_time"], reverse=True)[:10]
    prediction_count = int(await session.scalar(select(func.count()).select_from(Prediction)) or 0)
    def avg(values):
        return round(sum(values) / len(values), 2) if values else None
    return {
        "total_assets": len(payloads),
        "total_predictions": prediction_count,
        "total_bridges": by_type.get("bridge", 0),
        "total_dams": by_type.get("dam", 0),
        "total_barrages": by_type.get("barrage", 0),
        "total_ports": by_type.get("port", 0),
        "total_roads": by_type.get("road", 0),
        "total_buildings": by_type.get("building", 0),
        "total_airports": by_type.get("airport", 0),
        "total_power_plants": by_type.get("powerplant", 0) + by_type.get("power_plant", 0),
        "high_risk_assets": len(high),
        "medium_risk_assets": len(medium),
        "low_risk_assets": len(low),
        "average_health_score": avg(health_scores),
        "average_risk_score": avg(risk_scores),
        "average_remaining_life": avg(rul_values),
        "district_distribution": [{"district": k, "count": v} for k, v in districts.most_common()],
        "asset_type_distribution": [{"asset_type": k, "count": v} for k, v in by_type.most_common()],
        "risk_distribution": [
            {"key": "low", "name": "Low Risk", "value": len(low)},
            {"key": "medium", "name": "Medium Risk", "value": len(medium)},
            {"key": "high", "name": "High Risk", "value": len(high)},
        ],
        "top_high_risk_assets": [{
            "id": a["asset_code"], "name": a["name"], "asset_type": a["asset_type"], "district": a["district"],
            "risk_score": a["risk_score"], "health_score": a["health_score"], "remaining_life": a["remaining_useful_life"], "prediction_confidence": a.get("prediction_confidence"),
        } for a in top],
        "recent_assessments": [{
            "assessment_id": f"pred-{a['asset_code']}", "assessment_name": f"{a['name']} assessment", "asset_id": a["asset_code"],
            "risk_level": a["risk_level"], "health_score": a["health_score"], "last_assessed": a["prediction_time"],
        } for a in recent],
    }


@router.get("/analytics/risk-analysis")
async def risk_analysis(session: AsyncSession = Depends(get_db)):
    assets = (await session.scalars(select(Asset))).all()
    predictions = await _prediction_index(session)
    payloads = [_asset_payload(a, predictions) for a in assets]

    risk_distribution = [
        {"key": "low", "name": "Low Risk", "value": sum(1 for a in payloads if a.get("risk_score") is not None and float(a["risk_score"]) < 40)},
        {"key": "medium", "name": "Medium Risk", "value": sum(1 for a in payloads if a.get("risk_score") is not None and 40 <= float(a["risk_score"]) < 70)},
        {"key": "high", "name": "High Risk", "value": sum(1 for a in payloads if a.get("risk_score") is not None and float(a["risk_score"]) >= 70)},
    ]

    district_map = {}
    type_map = {}
    for item in payloads:
        district = str(item.get("district") or "Unknown")
        asset_type = str(item.get("asset_type") or "other")
        for key, bucket in ((district, district_map), (asset_type, type_map)):
            row = bucket.setdefault(key, {"assets": 0, "high_risk": 0, "medium_risk": 0, "low_risk": 0})
            row["assets"] += 1
            score = item.get("risk_score")
            if score is None:
                continue
            if float(score) >= 70:
                row["high_risk"] += 1
            elif float(score) >= 40:
                row["medium_risk"] += 1
            else:
                row["low_risk"] += 1

    district_risk = [{"district": key, **value} for key, value in sorted(district_map.items())]
    asset_type_risk = [{"asset_type": key, **value} for key, value in sorted(type_map.items())]
    top = sorted(
        [a for a in payloads if a.get("risk_score") is not None],
        key=lambda a: float(a["risk_score"]),
        reverse=True,
    )[:50]

    return {
        "risk_distribution": risk_distribution,
        "district_risk": district_risk,
        "asset_type_risk": asset_type_risk,
        "top_high_risk_assets": top,
    }


def _csv_response(rows, filename):
    stream = StringIO()
    if rows:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return Response(stream.getvalue(), media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/legacy-disabled/reports/assets/csv")
async def report_assets_csv(session: AsyncSession = Depends(get_db)):
    assets = (await session.scalars(select(Asset).order_by(Asset.id))).all()
    predictions = await _prediction_index(session)
    return _csv_response([_asset_payload(a, predictions) for a in assets], "simras-assets.csv")


def _pdf_bytes(lines: list[str]) -> bytes:
    def esc(text: str) -> str:
        return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    commands = ["BT", "/F1 12 Tf", "50 790 Td", "15 TL"]
    for line in lines:
        commands.append(f"({esc(line)}) Tj")
        commands.append("T*")
    commands.append("ET")
    stream = "\n".join(commands).encode("latin-1", errors="replace")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for i, obj in enumerate(objects, 1):
        offsets.append(len(out))
        out.extend(f"{i} 0 obj\n".encode())
        out.extend(obj)
        out.extend(b"\nendobj\n")
    xref = len(out)
    out.extend(f"xref\n0 {len(objects)+1}\n".encode())
    out.extend(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        out.extend(f"{off:010d} 00000 n \n".encode())
    out.extend(f"trailer\n<< /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    return bytes(out)


def _xlsx_bytes(rows: list[dict]) -> bytes:
    headers = list(rows[0].keys()) if rows else ["metric", "value"]
    def cell(ref: str, value) -> str:
        value = "" if value is None else str(value)
        return f'<c r="{ref}" t="inlineStr"><is><t>{html.escape(value)}</t></is></c>'
    def col_name(index: int) -> str:
        name = ""
        while index:
            index, rem = divmod(index - 1, 26)
            name = chr(65 + rem) + name
        return name
    xml_rows = []
    all_rows = [dict(zip(headers, headers))] + rows
    for r_idx, row in enumerate(all_rows, 1):
        cells = [cell(f"{col_name(c_idx)}{r_idx}", row.get(h, "")) for c_idx, h in enumerate(headers, 1)]
        xml_rows.append(f'<row r="{r_idx}">{"".join(cells)}</row>')
    sheet = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>' + ''.join(xml_rows) + '</sheetData></worksheet>'
    out = BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>')
        z.writestr("_rels/.rels", '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
        z.writestr("xl/workbook.xml", '<?xml version="1.0" encoding="UTF-8"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="SIMRAS Summary" sheetId="1" r:id="rId1"/></sheets></workbook>')
        z.writestr("xl/_rels/workbook.xml.rels", '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>')
        z.writestr("xl/worksheets/sheet1.xml", sheet)
    return out.getvalue()


@router.get("/legacy-disabled/reports/summary/xlsx")
async def report_summary_download(session: AsyncSession = Depends(get_db)):
    overview = await dashboard_overview(session)
    rows = [{"metric": k, "value": v} for k, v in overview.items() if isinstance(v, (int, float, str))]
    return Response(_xlsx_bytes(rows), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": 'attachment; filename="simras-summary.xlsx"'})


@router.get("/legacy-disabled/reports/asset/{identifier}/pdf")
async def report_asset_pdf(identifier: str, session: AsyncSession = Depends(get_db)):
    asset = await _find_asset(session, identifier)
    predictions = await _prediction_index(session)
    p = _asset_payload(asset, predictions)
    lines = [
        "SIMRAS Asset Report",
        f"Asset: {p['name']} ({p['asset_code']})",
        f"Type: {p['asset_type']}",
        f"District: {p['district']}",
        f"Identity: {p['identity_status']}",
        f"Health score: {p['health_score'] if p['health_score'] is not None else 'WITHHELD/UNAVAILABLE'}",
        f"Risk score: {p['risk_score'] if p['risk_score'] is not None else 'WITHHELD/UNAVAILABLE'}",
        f"Risk level: {p['risk_level']}",
        f"Prediction time: {p['prediction_time'] or 'N/A'}",
        "Decision-support output only; not an official engineering condition rating.",
    ]
    return Response(_pdf_bytes(lines), media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{identifier}-SIMRAS-report.pdf"'})

# === SIMRAS_REAL_REPORTS_START ===

async def _report_asset_predictions(session: AsyncSession, asset_id: int):
    rows = (await session.scalars(
        select(Prediction)
        .where(Prediction.asset_id == asset_id)
        .order_by(desc(Prediction.prediction_time))
    )).all()
    latest = {}
    for row in rows:
        latest.setdefault(str(row.target).lower(), row)
    return latest


def _fmt(value, suffix=""):
    if value is None:
        return "N/A"
    return f"{value}{suffix}"


async def _latest_model_registry(session: AsyncSession):
    try:
        result = await session.execute(text("SELECT * FROM model_registry ORDER BY id DESC LIMIT 1"))
        row = result.mappings().first()
        return dict(row) if row else None
    except Exception:
        return None


@router.get("/legacy-disabled/reports/catalog")
async def reports_catalog():
    return {
        "items": [
            {"id": "asset_condition", "title": "Asset Condition Report", "category": "Asset Condition", "format": "PDF", "requires_asset": True, "description": "Identity, condition and latest decision-support health/risk state for one real asset."},
            {"id": "inspection", "title": "Inspection Report", "category": "Inspection", "format": "PDF", "requires_asset": True, "description": "Recorded inspection history and findings from the database."},
            {"id": "maintenance", "title": "Maintenance Report", "category": "Maintenance", "format": "PDF", "requires_asset": True, "description": "Recorded maintenance actions, status, cost and dates from the database."},
            {"id": "risk", "title": "Risk Assessment Report", "category": "Risk", "format": "PDF", "requires_asset": True, "description": "Latest stored risk prediction, confidence, bounds and model metadata."},
            {"id": "ai_prediction", "title": "AI Prediction Report", "category": "AI Prediction", "format": "PDF", "requires_asset": True, "description": "Latest stored health, risk and RUL outputs with governance status."},
            {"id": "twin_evidence", "title": "Digital Twin Evidence Report", "category": "Digital Twin", "format": "PDF", "requires_asset": True, "description": "Identity, coordinates, source-linked characteristics and evidence availability."},
            {"id": "high_risk", "title": "High-Risk Asset Register", "category": "Risk", "format": "CSV", "requires_asset": False, "description": "Portfolio assets whose stored risk score is at or above the high-risk threshold."},
            {"id": "asset_register", "title": "Asset Register", "category": "Infrastructure", "format": "CSV", "requires_asset": False, "description": "Real asset register with current stored prediction fields."},
            {"id": "district_analytics", "title": "District Analytics Report", "category": "Analytics", "format": "PDF", "requires_asset": False, "requires_district": True, "description": "District asset counts and current risk/health coverage."},
            {"id": "model_governance", "title": "Model Governance Report", "category": "Model Governance", "format": "PDF", "requires_asset": False, "description": "Latest model registry stage, version, metrics and governance metadata."},
            {"id": "portfolio", "title": "Portfolio Executive Report", "category": "Analytics", "format": "PDF", "requires_asset": False, "description": "Current Andhra Pradesh portfolio counts and decision-support risk summary."},
            {"id": "summary_xlsx", "title": "Portfolio Excel Summary", "category": "Analytics", "format": "XLSX", "requires_asset": False, "description": "Spreadsheet summary generated from the live database."},
        ]
    }


@router.get("/legacy-disabled/reports/asset/{identifier}/inspection/pdf")
async def report_asset_inspection_pdf(identifier: str, session: AsyncSession = Depends(get_db)):
    asset = await _find_asset(session, identifier)
    date_col = getattr(Inspection, "inspection_date", Inspection.id)
    rows = (await session.scalars(
        select(Inspection)
        .where(Inspection.asset_id == asset.id)
        .order_by(desc(date_col))
        .limit(12)
    )).all()
    lines = [
        "SIMRAS Inspection Report",
        f"Asset: {asset.name} ({asset.asset_code})",
        f"District: {_value(asset, 'district', default='N/A')}",
        f"Inspection records: {len(rows)}",
    ]
    if not rows:
        lines.append("No inspection records are currently stored for this asset.")
    for idx, row in enumerate(rows, 1):
        lines.extend([
            f"Inspection {idx}",
            f"Date: {_iso(_value(row, 'inspection_date')) or 'N/A'}",
            f"Type: {_value(row, 'inspection_type', default='N/A')}",
            f"Inspector: {_value(row, 'inspector', 'inspector_name', default='N/A')}",
            f"Condition: {_value(row, 'condition', default='N/A')}",
            f"Score: {_fmt(_value(row, 'score', 'condition_score', 'inspection_score'))}",
            f"Findings: {_value(row, 'findings', 'notes', 'remarks', default='N/A')}",
        ])
    return Response(_pdf_bytes(lines), media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{identifier}-inspection-report.pdf"'})


@router.get("/legacy-disabled/reports/asset/{identifier}/maintenance/pdf")
async def report_asset_maintenance_pdf(identifier: str, session: AsyncSession = Depends(get_db)):
    asset = await _find_asset(session, identifier)
    date_col = getattr(Maintenance, "maintenance_date", Maintenance.id)
    rows = (await session.scalars(
        select(Maintenance)
        .where(Maintenance.asset_id == asset.id)
        .order_by(desc(date_col))
        .limit(12)
    )).all()
    lines = [
        "SIMRAS Maintenance Report",
        f"Asset: {asset.name} ({asset.asset_code})",
        f"District: {_value(asset, 'district', default='N/A')}",
        f"Maintenance records: {len(rows)}",
    ]
    if not rows:
        lines.append("No maintenance records are currently stored for this asset.")
    for idx, row in enumerate(rows, 1):
        lines.extend([
            f"Maintenance {idx}",
            f"Type: {_value(row, 'maintenance_type', 'action', default='N/A')}",
            f"Status: {_value(row, 'status', default='N/A')}",
            f"Priority: {_value(row, 'priority', default='N/A')}",
            f"Date: {_iso(_value(row, 'maintenance_date', 'planned_start_date')) or 'N/A'}",
            f"Completed: {_iso(_value(row, 'actual_completion_date')) or 'N/A'}",
            f"Cost: {_fmt(_value(row, 'cost', 'estimated_cost', 'actual_cost'))}",
            f"Performed by: {_value(row, 'performed_by', 'assigned_contractor', default='N/A')}",
            f"Description: {_value(row, 'description', 'action', default='N/A')}",
        ])
    return Response(_pdf_bytes(lines), media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{identifier}-maintenance-report.pdf"'})


@router.get("/legacy-disabled/reports/asset/{identifier}/risk/pdf")
async def report_asset_risk_pdf(identifier: str, session: AsyncSession = Depends(get_db)):
    asset = await _find_asset(session, identifier)
    latest = await _report_asset_predictions(session, asset.id)
    risk = latest.get("risk")
    lines = [
        "SIMRAS Risk Assessment Report",
        f"Asset: {asset.name} ({asset.asset_code})",
        f"District: {_value(asset, 'district', default='N/A')}",
        f"Risk score: {_fmt(_value(risk, 'value'))}",
        f"Risk class: {_value(risk, 'predicted_class', default='N/A')}",
        f"Confidence: {_fmt(_value(risk, 'confidence_score'))}",
        f"Lower bound: {_fmt(_value(risk, 'lower_bound'))}",
        f"Upper bound: {_fmt(_value(risk, 'upper_bound'))}",
        f"Model version: {_value(risk, 'model_version', default='N/A')}",
        f"Feature version: {_value(risk, 'feature_version', default='N/A')}",
        f"Prediction time: {_iso(_value(risk, 'prediction_time')) or 'N/A'}",
        f"Governance status: {_value(risk, 'status', default='UNAVAILABLE')}",
        "Decision-support output only; not an official engineering condition rating.",
    ]
    return Response(_pdf_bytes(lines), media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{identifier}-risk-report.pdf"'})


@router.get("/legacy-disabled/reports/asset/{identifier}/ai/pdf")
async def report_asset_ai_pdf(identifier: str, session: AsyncSession = Depends(get_db)):
    asset = await _find_asset(session, identifier)
    latest = await _report_asset_predictions(session, asset.id)
    lines = [
        "SIMRAS AI Prediction Report",
        f"Asset: {asset.name} ({asset.asset_code})",
        "Stored latest predictions:",
    ]
    if not latest:
        lines.append("No stored AI prediction is currently available for this asset.")
    for target in ("health", "risk", "rul", "remaining_life"):
        row = latest.get(target)
        if row is None:
            continue
        lines.extend([
            f"Target: {target}",
            f"Value: {_fmt(_value(row, 'value'))}",
            f"Class: {_value(row, 'predicted_class', default='N/A')}",
            f"Bounds: {_fmt(_value(row, 'lower_bound'))} to {_fmt(_value(row, 'upper_bound'))}",
            f"Confidence: {_fmt(_value(row, 'confidence_score'))}",
            f"Model: {_value(row, 'model_version', default='N/A')}",
            f"Feature version: {_value(row, 'feature_version', default='N/A')}",
            f"Status: {_value(row, 'status', default='UNAVAILABLE')}",
            f"Time: {_iso(_value(row, 'prediction_time')) or 'N/A'}",
        ])
    lines.append("Unavailable or withheld values are intentionally not fabricated.")
    return Response(_pdf_bytes(lines), media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{identifier}-ai-prediction-report.pdf"'})


@router.get("/legacy-disabled/reports/asset/{identifier}/twin-evidence/pdf")
async def report_asset_twin_evidence_pdf(identifier: str, session: AsyncSession = Depends(get_db)):
    asset = await _find_asset(session, identifier)
    predictions = await _prediction_index(session)
    p = _asset_payload(asset, predictions)
    lines = [
        "SIMRAS Digital Twin Evidence Report",
        f"Asset: {p['name']} ({p['asset_code']})",
        f"Type: {p['asset_type']}",
        f"District: {p['district']}",
        f"Identity status: {p['identity_status']}",
        f"Latitude: {_fmt(p['latitude'])}",
        f"Longitude: {_fmt(p['longitude'])}",
        f"Built year: {_fmt(p['built_year'])}",
        f"Design life: {_fmt(p['design_life'])}",
        f"Material: {_fmt(p['material'])}",
        f"Owner: {_fmt(p['owner'])}",
        f"Condition: {_fmt(p['condition'])}",
        f"Prediction time: {p['prediction_time'] or 'N/A'}",
        "Only linked database values are shown; missing evidence remains N/A.",
    ]
    return Response(_pdf_bytes(lines), media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{identifier}-twin-evidence-report.pdf"'})


@router.get("/legacy-disabled/reports/high-risk/csv")
async def report_high_risk_csv(session: AsyncSession = Depends(get_db)):
    assets = (await session.scalars(select(Asset).order_by(Asset.id))).all()
    predictions = await _prediction_index(session)
    rows = [_asset_payload(a, predictions) for a in assets]
    rows = [row for row in rows if row.get("risk_score") is not None and float(row["risk_score"]) >= 70]
    rows.sort(key=lambda row: float(row["risk_score"]), reverse=True)
    return _csv_response(rows, "simras-high-risk-assets.csv")


@router.get("/legacy-disabled/reports/district/{district}/pdf")
async def report_district_pdf(district: str, session: AsyncSession = Depends(get_db)):
    stmt = select(Asset).where(Asset.district == district) if hasattr(Asset, "district") else select(Asset)
    assets = (await session.scalars(stmt.order_by(Asset.id))).all()
    predictions = await _prediction_index(session)
    payloads = [_asset_payload(a, predictions) for a in assets]
    risk_values = [float(x["risk_score"]) for x in payloads if x.get("risk_score") is not None]
    health_values = [float(x["health_score"]) for x in payloads if x.get("health_score") is not None]
    high = sum(1 for x in payloads if x.get("risk_score") is not None and float(x["risk_score"]) >= 70)
    lines = [
        "SIMRAS District Analytics Report",
        f"District: {district}",
        f"Assets: {len(payloads)}",
        f"Assets with risk prediction: {len(risk_values)}",
        f"High-risk assets: {high}",
        f"Average risk: {round(sum(risk_values)/len(risk_values), 2) if risk_values else 'N/A'}",
        f"Assets with health prediction: {len(health_values)}",
        f"Average health: {round(sum(health_values)/len(health_values), 2) if health_values else 'N/A'}",
    ]
    return Response(_pdf_bytes(lines), media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{district}-SIMRAS-analytics.pdf"'})


@router.get("/legacy-disabled/reports/model-governance/pdf")
async def report_model_governance_pdf(session: AsyncSession = Depends(get_db)):
    model = await _latest_model_registry(session)
    if not model:
        lines = ["SIMRAS Model Governance Report", "No model_registry record is currently available."]
    else:
        metrics = model.get("metrics")
        lines = [
            "SIMRAS Model Governance Report",
            f"Model: {model.get('model_name', 'N/A')}",
            f"Version: {model.get('version', 'N/A')}",
            f"Stage: {model.get('stage', 'N/A')}",
            f"Feature version: {model.get('feature_version', 'N/A')}",
            f"Training dataset: {model.get('training_dataset', 'N/A')}",
            f"Artifact URI: {model.get('artifact_uri', 'N/A')}",
            f"Checksum: {model.get('checksum', 'N/A')}",
            f"Metrics: {str(metrics)[:1000] if metrics is not None else 'N/A'}",
        ]
    return Response(_pdf_bytes(lines), media_type="application/pdf", headers={"Content-Disposition": 'attachment; filename="SIMRAS-model-governance.pdf"'})


@router.get("/legacy-disabled/reports/portfolio/pdf")
async def report_portfolio_pdf(session: AsyncSession = Depends(get_db)):
    overview = await dashboard_overview(session)
    lines = [
        "SIMRAS Andhra Pradesh Portfolio Report",
        f"Total assets: {overview.get('total_assets', 0)}",
        f"Bridges: {overview.get('total_bridges', 0)}",
        f"Dams: {overview.get('total_dams', 0)}",
        f"Barrages: {overview.get('total_barrages', 0)}",
        f"Airports: {overview.get('total_airports', 0)}",
        f"High risk: {overview.get('high_risk_assets', 0)}",
        f"Medium risk: {overview.get('medium_risk_assets', 0)}",
        f"Low risk: {overview.get('low_risk_assets', 0)}",
        f"Average health: {_fmt(overview.get('average_health_score'))}",
        f"Average risk: {_fmt(overview.get('average_risk_score'))}",
        "Counts are generated from the current database at request time.",
    ]
    return Response(_pdf_bytes(lines), media_type="application/pdf", headers={"Content-Disposition": 'attachment; filename="SIMRAS-portfolio-report.pdf"'})

# === SIMRAS_REAL_REPORTS_END ===
