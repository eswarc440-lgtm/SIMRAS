from __future__ import annotations

from io import BytesIO
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.evidence_state_service import build_evidence_state
from app.services.real_report_service import build_real_report_payload
from app.services.twin_service import build_twin

router = APIRouter(prefix="/real-reports", tags=["real-reports"])


def _label(value: str) -> str:
    return value.replace("_", " ").strip().title()


def _scalar_text(value: Any) -> str:
    if isinstance(value, bool):
        return "Yes" if value else "No"
    return str(value)


def _rows(mapping: dict[str, Any]) -> list[list[str]]:
    rows: list[list[str]] = []
    for key, value in mapping.items():
        if isinstance(value, dict):
            for child_key, child_value in value.items():
                if isinstance(child_value, (dict, list)):
                    continue
                rows.append([f"{_label(key)} · {_label(child_key)}", _scalar_text(child_value)])
        elif isinstance(value, list):
            continue
        else:
            rows.append([_label(key), _scalar_text(value)])
    return rows


def _add_section(story: list[Any], title: str, mapping: dict[str, Any], styles: Any) -> None:
    rows = _rows(mapping)
    if not rows:
        return

    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph(title, styles["Heading2"]))
    table = Table(rows, colWidths=[62 * mm, 118 * mm], repeatRows=0)
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#415466")),
                ("TEXTCOLOR", (1, 0), (1, -1), colors.HexColor("#101820")),
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F0F6F8")),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CDD9DF")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(table)


def _render_pdf(payload: dict[str, Any]) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        title=f"SIMRAS Real Infrastructure Report - {payload.get('asset_code', '')}",
        author="SIMRAS",
    )
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="ReportTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#0A5166"),
            alignment=TA_CENTER,
            spaceAfter=4 * mm,
        )
    )
    styles["Heading2"].textColor = colors.HexColor("#0A5166")
    styles["Heading2"].fontSize = 11

    asset = payload.get("asset") or {}
    asset_name = asset.get("name") or asset.get("asset_name") or payload.get("asset_code")

    story: list[Any] = [
        Paragraph("SIMRAS — Evidence-Backed Infrastructure Report", styles["ReportTitle"]),
        Paragraph(
            f"<b>{asset_name}</b> &nbsp; | &nbsp; {payload.get('asset_code', '')}",
            styles["Normal"],
        ),
        Spacer(1, 2 * mm),
        Paragraph(
            "Only available source-backed facts and eligible validated model outputs are included. "
            "Unavailable or insufficient fields are omitted rather than replaced with placeholder values.",
            styles["BodyText"],
        ),
    ]

    sections = (
        ("Asset identity", payload.get("asset")),
        ("Official asset facts", payload.get("official_asset_facts")),
        ("Government / authoritative engineering evidence", payload.get("government_engineering")),
        ("Digital twin provenance", payload.get("digital_twin")),
        ("Current real environment observations", payload.get("real_environment_observations")),
        ("Latest real inspection", payload.get("real_inspection")),
        ("Eligible locally validated ML prediction", payload.get("ml_prediction")),
        ("Evidence provenance", payload.get("evidence")),
    )
    for title, section in sections:
        if isinstance(section, dict) and section:
            _add_section(story, title, section, styles)

    maintenance = payload.get("real_maintenance")
    if isinstance(maintenance, list) and maintenance:
        story.append(Spacer(1, 4 * mm))
        story.append(Paragraph("Real maintenance records", styles["Heading2"]))
        for index, record in enumerate(maintenance, start=1):
            if not isinstance(record, dict):
                continue
            story.append(Paragraph(f"Record {index}", styles["Heading3"]))
            _add_section(story, "", record, styles)

    doc.build(story)
    return buffer.getvalue()


async def _payload(session: AsyncSession, asset_code: str) -> dict[str, Any]:
    twin = await build_twin(session, asset_code)
    evidence = await build_evidence_state(session, asset_code)
    return build_real_report_payload(asset_code, twin, evidence)


@router.get("/{asset_code}")
async def real_asset_report(
    asset_code: str,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    return await _payload(session, asset_code)


@router.get("/{asset_code}/pdf")
async def real_asset_report_pdf(
    asset_code: str,
    session: AsyncSession = Depends(get_db),
) -> Response:
    payload = await _payload(session, asset_code)
    body = _render_pdf(payload)
    safe_code = "".join(ch for ch in asset_code if ch.isalnum() or ch in {"-", "_"})
    return Response(
        content=body,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="SIMRAS_{safe_code}_REAL_REPORT.pdf"',
            "X-SIMRAS-Report-Mode": "REAL_EVIDENCE_ONLY",
        },
    )
