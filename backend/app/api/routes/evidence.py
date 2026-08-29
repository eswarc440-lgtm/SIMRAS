from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.evidence_state_service import build_evidence_state


router = APIRouter(prefix="/assets", tags=["evidence"])


@router.get("/{asset_code}/state")
async def get_asset_evidence_state(
    asset_code: str,
    session: AsyncSession = Depends(get_db),
) -> dict:
    return await build_evidence_state(session, asset_code)
