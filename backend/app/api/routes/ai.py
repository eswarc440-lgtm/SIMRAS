from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import require_admin_key
from app.db.session import get_db
from app.services.ai_advisor import AmbiguousAssetError, build_ai_context

router = APIRouter(prefix="/ai", tags=["ai"])

class AiQuestion(BaseModel):
    prompt: str = Field(min_length=1, max_length=4000)

@router.post("/assets/{asset_code}/context", dependencies=[Depends(require_admin_key)])
async def asset_context(asset_code: str, request: AiQuestion, session: AsyncSession = Depends(get_db)):
    if not request.prompt.strip():
        raise HTTPException(status_code=422, detail="Prompt is required")
    try:
        return await build_ai_context(session, asset_code, request.prompt.strip())
    except AmbiguousAssetError as error:
        raise HTTPException(status_code=409, detail={"error": str(error), "choices": error.choices}) from error
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

@router.post("/assets/{asset_code}/ask")
async def gateway_only():
    raise HTTPException(status_code=410, detail="Use the authenticated SIMRAS Node gateway advisor endpoint. Gemini is configured only on that server.")
