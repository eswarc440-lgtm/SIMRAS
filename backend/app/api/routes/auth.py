from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    PasswordChangeRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    UserCreate,
    UserResponse,
    UserUpdate,
)
from app.services.auth_service import (
    authenticate_user,
    change_password,
    create_password_reset_token,
    create_user,
    create_user_session,
    reset_password,
    revoke_all_user_sessions,
    revoke_session,
    validate_password_reset_token,
    validate_session,
)
from app.services.rbac_service import is_admin, is_reviewer

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/login", response_model=LoginResponse)
async def login(
    login_data: LoginRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> LoginResponse:
    """Authenticate user and create session."""
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    user, error = await authenticate_user(
        session,
        login_data.email,
        login_data.password,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error or "Authentication failed",
        )

    # Create session
    user_session = await create_user_session(
        session,
        user,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    # Set HTTPOnly cookie
    response = Response()
    response.set_cookie(
        key="session_token",
        value=user_session.session_token,
        httponly=True,
        secure=True,  # True in production with HTTPS
        samesite="lax",
        expires=user_session.expires_at,
    )

    return LoginResponse(
        access_token=user_session.session_token,
        user=UserResponse.model_validate(user),
        expires_at=user_session.expires_at,
    )


@router.post("/logout")
async def logout(
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Logout user and revoke session."""
    session_token = request.cookies.get("session_token")

    if session_token:
        await revoke_session(session, session_token)

    response = Response()
    response.delete_cookie(key="session_token")

    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: Any = Depends(get_current_user),
) -> UserResponse:
    """Get current user information."""
    return UserResponse.model_validate(current_user)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    session: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> UserResponse:
    """Register a new user (admin only)."""
    # Only admins can create users
    if not await is_admin(session, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can create users",
        )

    # Check if email already exists
    from sqlalchemy import select

    from app.models.operational import User

    result = await session.execute(select(User).where(User.email == user_data.email))
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    user = await create_user(session, user_data, created_by=current_user.id)
    return UserResponse.model_validate(user)


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    session: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> UserResponse:
    """Update current user profile."""
    from sqlalchemy import select

    from app.models.operational import User

    result = await session.execute(select(User).where(User.id == current_user.id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Update fields
    if user_update.name is not None:
        user.name = user_update.name
    if user_update.phone is not None:
        user.phone = user_update.phone
    if user_update.department is not None:
        user.department = user_update.department
    if user_update.designation is not None:
        user.designation = user_update.designation
    if user_update.district is not None:
        user.district = user_update.district

    user.updated_at = datetime.now(UTC)

    await session.commit()
    await session.refresh(user)

    return UserResponse.model_validate(user)


@router.post("/change-password")
async def change_password_endpoint(
    password_data: PasswordChangeRequest,
    session: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> dict[str, str]:
    """Change current user's password."""
    success, error = await change_password(
        session,
        current_user.id,
        password_data.old_password,
        password_data.new_password,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error or "Password change failed",
        )

    # Revoke all sessions for security
    await revoke_all_user_sessions(session, current_user.id)

    return {"message": "Password changed successfully. Please login again."}


@router.post("/password-reset")
async def request_password_reset(
    reset_request: PasswordResetRequest,
    session: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Request a password reset token."""
    reset_token = await create_password_reset_token(session, reset_request.email)

    if reset_token is None:
        # Don't reveal if email exists
        return {"message": "If the email exists, a reset token has been sent"}

    # In production, send email with reset token
    # For now, return the token (development only)
    return {
        "message": "Password reset token created",
        "token": reset_token.token,  # Remove in production
    }


@router.post("/password-reset/confirm")
async def confirm_password_reset(
    reset_confirm: PasswordResetConfirm,
    session: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Reset password using token."""
    success, error = await reset_password(
        session,
        reset_confirm.token,
        reset_confirm.new_password,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error or "Password reset failed",
        )

    return {"message": "Password reset successfully"}


@router.post("/refresh")
async def refresh_session(
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> LoginResponse:
    """Refresh user session."""
    session_token = request.cookies.get("session_token")

    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No session token provided",
        )

    user = await validate_session(session, session_token)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
        )

    # Create new session
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    new_session = await create_user_session(
        session,
        user,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    # Revoke old session
    await revoke_session(session, session_token)

    # Set new cookie
    response = Response()
    response.set_cookie(
        key="session_token",
        value=new_session.session_token,
        httponly=True,
        secure=True,
        samesite="lax",
        expires=new_session.expires_at,
    )

    return LoginResponse(
        access_token=new_session.session_token,
        user=UserResponse.model_validate(user),
        expires_at=new_session.expires_at,
    )
