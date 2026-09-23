from __future__ import annotations

from typing import Any

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.operational import User
from app.services.auth_service import validate_session


async def get_current_user(
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> User:
    """Get current authenticated user from session token."""
    session_token = request.cookies.get("session_token")

    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    user = await validate_session(session, session_token)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
        )

    return user


async def get_current_officer(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get current authenticated officer (OFFICER, REVIEWER, or ADMIN)."""
    if current_user.role not in {"OFFICER", "REVIEWER", "ADMIN"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Officer access required",
        )

    return current_user


async def get_current_reviewer(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get current authenticated reviewer (REVIEWER or ADMIN)."""
    if current_user.role not in {"REVIEWER", "ADMIN"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Reviewer access required",
        )

    return current_user


async def get_current_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get current authenticated admin."""
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    return current_user


async def get_optional_user(
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> User | None:
    """Get current user if authenticated, otherwise return None."""
    session_token = request.cookies.get("session_token")

    if not session_token:
        return None

    user = await validate_session(session, session_token)
    return user
