from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_officer, get_current_user, get_db
from app.services.ai_assistant import ai_assistant_service

router = APIRouter(prefix="/reports/{asset_code}/assistant", tags=["ai-assistant"])


@router.post("")
async def ask_ai(
    asset_code: str,
    question: str,
    session: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> dict[str, Any]:
    """Ask AI assistant about an asset (OFFICER+ only)."""
    # Public users can ask basic questions, officers get full access
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required for AI assistant",
        )

    response = await ai_assistant_service.generate_response(
        asset_code=asset_code,
        question=question,
        session=session,
        user_id=current_user.id,
    )

    return response


@router.post("/summary")
async def get_ai_summary(
    asset_code: str,
    session: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> dict[str, Any]:
    """Get AI-generated summary of asset (OFFICER+ only)."""
    summary_question = f"Provide a comprehensive summary of this asset including health, risk, RUL, and key operational information."

    response = await ai_assistant_service.generate_response(
        asset_code=asset_code,
        question=summary_question,
        session=session,
        user_id=current_user.id if current_user else None,
    )

    return response


@router.post("/explain-health")
async def explain_health(
    asset_code: str,
    session: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> dict[str, Any]:
    """Explain health assessment (OFFICER+ only)."""
    question = "Why is the health score this value? Explain the health assessment basis and contributing factors."

    response = await ai_assistant_service.generate_response(
        asset_code=asset_code,
        question=question,
        session=session,
        user_id=current_user.id if current_user else None,
    )

    return response


@router.post("/explain-risk")
async def explain_risk(
    asset_code: str,
    session: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> dict[str, Any]:
    """Explain risk assessment (OFFICER+ only)."""
    question = "Why is the risk level what it is? Explain the risk assessment basis and contributing factors."

    response = await ai_assistant_service.generate_response(
        asset_code=asset_code,
        question=question,
        session=session,
        user_id=current_user.id if current_user else None,
    )

    return response


@router.post("/explain-rul")
async def explain_rul(
    asset_code: str,
    session: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> dict[str, Any]:
    """Explain RUL assessment (OFFICER+ only)."""
    question = "Why is the remaining useful life this value? Explain the RUL calculation basis and methodology."

    response = await ai_assistant_service.generate_response(
        asset_code=asset_code,
        question=question,
        session=session,
        user_id=current_user.id if current_user else None,
    )

    return response


@router.post("/draft-plan")
async def draft_maintenance_plan(
    asset_code: str,
    session: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_officer),
) -> dict[str, Any]:
    """Draft a maintenance plan (OFFICER only)."""
    question = "Draft a maintenance plan based on the current asset condition and any identified issues. Include priority, proposed actions, and affected components."

    response = await ai_assistant_service.generate_response(
        asset_code=asset_code,
        question=question,
        session=session,
        user_id=current_user.id,
    )

    # Add disclaimer that this is decision-support only
    response["disclaimer"] = "This is an AI-generated draft for decision-support purposes only. It must be reviewed by an officer and approved by a reviewer before implementation."

    return response
