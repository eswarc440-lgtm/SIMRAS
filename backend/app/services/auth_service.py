from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.operational import (
    LoginAudit,
    PasswordResetToken,
    User,
    UserSession,
)
from app.schemas.auth import LoginRequest, UserCreate, UserResponse

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


async def create_user(
    session: AsyncSession,
    user_data: UserCreate,
    created_by: int | None = None,
) -> User:
    """Create a new user with hashed password."""
    user = User(
        officer_id=user_data.officer_id,
        name=user_data.name,
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        role=user_data.role,
        department=user_data.department,
        designation=user_data.designation,
        district=user_data.district,
        phone=user_data.phone,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def authenticate_user(
    session: AsyncSession,
    email: str,
    password: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> tuple[User | None, str | None]:
    """
    Authenticate a user by email and password.
    Returns (user, error_message) tuple.
    """
    # Find user by email
    result = await session.execute(
        select(User).where(User.email == email, User.is_active == True)
    )
    user = result.scalar_one_or_none()

    if user is None:
        # Log failed login attempt
        await log_login_attempt(
            session,
            user_id=None,
            action="LOGIN",
            ip_address=ip_address,
            user_agent=user_agent,
            success=False,
            failure_reason="User not found or inactive",
        )
        return None, "Invalid email or password"

    if not verify_password(password, user.password_hash):
        # Log failed login attempt
        await log_login_attempt(
            session,
            user_id=user.id,
            action="LOGIN",
            ip_address=ip_address,
            user_agent=user_agent,
            success=False,
            failure_reason="Invalid password",
        )
        return None, "Invalid email or password"

    # Update last login
    user.last_login = datetime.now(UTC)
    user.login_count = (user.login_count or 0) + 1

    # Log successful login
    await log_login_attempt(
        session,
        user_id=user.id,
        action="LOGIN",
        ip_address=ip_address,
        user_agent=user_agent,
        success=True,
    )

    await session.commit()
    await session.refresh(user)

    return user, None


async def create_user_session(
    session: AsyncSession,
    user: User,
    ip_address: str | None = None,
    user_agent: str | None = None,
    expires_hours: int = 24,
) -> UserSession:
    """Create a new user session."""
    import secrets

    session_token = secrets.token_urlsafe(32)
    expires_at = datetime.now(UTC) + timedelta(hours=expires_hours)

    user_session = UserSession(
        user_id=user.id,
        session_token=session_token,
        expires_at=expires_at,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    session.add(user_session)
    await session.commit()
    await session.refresh(user_session)

    return user_session


async def validate_session(
    session: AsyncSession,
    session_token: str,
) -> User | None:
    """Validate a session token and return the user if valid."""
    result = await session.execute(
        select(UserSession)
        .where(
            UserSession.session_token == session_token,
            UserSession.is_active == True,
            UserSession.expires_at > datetime.now(UTC),
        )
        .join(User)
    )
    user_session = result.scalar_one_or_none()

    if user_session is None:
        return None

    return user_session.user


async def revoke_session(session: AsyncSession, session_token: str) -> bool:
    """Revoke a session token."""
    result = await session.execute(
        select(UserSession).where(UserSession.session_token == session_token)
    )
    user_session = result.scalar_one_or_none()

    if user_session is None:
        return False

    user_session.is_active = False
    await session.commit()
    return True


async def revoke_all_user_sessions(session: AsyncSession, user_id: int) -> int:
    """Revoke all sessions for a user."""
    result = await session.execute(
        select(UserSession).where(
            UserSession.user_id == user_id, UserSession.is_active == True
        )
    )
    sessions = result.scalars().all()

    for session_obj in sessions:
        session_obj.is_active = False

    await session.commit()
    return len(sessions)


async def log_login_attempt(
    session: AsyncSession,
    user_id: int | None,
    action: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
    success: bool = True,
    failure_reason: str | None = None,
) -> LoginAudit:
    """Log a login attempt for audit purposes."""
    audit = LoginAudit(
        user_id=user_id,
        action=action,
        ip_address=ip_address,
        user_agent=user_agent,
        success=success,
        failure_reason=failure_reason,
        created_at=datetime.now(UTC),
    )
    session.add(audit)
    await session.commit()
    await session.refresh(audit)
    return audit


async def change_password(
    session: AsyncSession,
    user_id: int,
    old_password: str,
    new_password: str,
) -> tuple[bool, str | None]:
    """Change a user's password."""
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        return False, "User not found"

    if not verify_password(old_password, user.password_hash):
        return False, "Current password is incorrect"

    user.password_hash = get_password_hash(new_password)
    await session.commit()

    return True, None


async def create_password_reset_token(
    session: AsyncSession,
    email: str,
    expires_hours: int = 24,
) -> PasswordResetToken | None:
    """Create a password reset token for a user."""
    import secrets

    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user is None:
        return None

    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(UTC) + timedelta(hours=expires_hours)

    reset_token = PasswordResetToken(
        user_id=user.id,
        token=token,
        expires_at=expires_at,
    )
    session.add(reset_token)
    await session.commit()
    await session.refresh(reset_token)

    return reset_token


async def validate_password_reset_token(
    session: AsyncSession,
    token: str,
) -> User | None:
    """Validate a password reset token and return the user if valid."""
    result = await session.execute(
        select(PasswordResetToken)
        .where(
            PasswordResetToken.token == token,
            PasswordResetToken.is_used == False,
            PasswordResetToken.expires_at > datetime.now(UTC),
        )
        .join(User)
    )
    reset_token = result.scalar_one_or_none()

    if reset_token is None:
        return None

    return reset_token.user


async def reset_password(
    session: AsyncSession,
    token: str,
    new_password: str,
) -> tuple[bool, str | None]:
    """Reset a user's password using a reset token."""
    user = await validate_password_reset_token(session, token)

    if user is None:
        return False, "Invalid or expired reset token"

    result = await session.execute(
        select(PasswordResetToken).where(PasswordResetToken.token == token)
    )
    reset_token = result.scalar_one_or_none()

    user.password_hash = get_password_hash(new_password)
    reset_token.is_used = True
    reset_token.used_at = datetime.now(UTC)

    await session.commit()

    return True, None
