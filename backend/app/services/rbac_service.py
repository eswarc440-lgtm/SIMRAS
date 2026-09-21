from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.operational import RolePermission, User


# Role definitions
ROLES = {
    "PUBLIC": "public access - view only",
    "OFFICER": "officer - can create inspections, maintenance, plans",
    "REVIEWER": "reviewer - can approve/reject submissions",
    "ADMIN": "admin - full system access",
}

# Default permissions by role
DEFAULT_PERMISSIONS = {
    "PUBLIC": [
        ("view", "gis"),
        ("view", "digital_twin"),
        ("view", "inspections"),
        ("view", "maintenance"),
        ("view", "reports"),
        ("download", "reports"),
        ("view", "evidence"),
    ],
    "OFFICER": [
        # All PUBLIC permissions
        ("view", "gis"),
        ("view", "digital_twin"),
        ("view", "inspections"),
        ("view", "maintenance"),
        ("view", "reports"),
        ("download", "reports"),
        ("view", "evidence"),
        # OFFICER-specific
        ("create", "asset"),
        ("submit", "inspection"),
        ("create", "maintenance"),
        ("upload", "evidence"),
        ("create", "plan"),
        ("use", "ai"),
    ],
    "REVIEWER": [
        # All OFFICER permissions
        ("view", "gis"),
        ("view", "digital_twin"),
        ("view", "inspections"),
        ("view", "maintenance"),
        ("view", "reports"),
        ("download", "reports"),
        ("view", "evidence"),
        ("create", "asset"),
        ("submit", "inspection"),
        ("create", "maintenance"),
        ("upload", "evidence"),
        ("create", "plan"),
        ("use", "ai"),
        # REVIEWER-specific
        ("review", "asset"),
        ("approve", "asset"),
        ("reject", "asset"),
        ("review", "inspection"),
        ("approve", "inspection"),
        ("reject", "inspection"),
        ("review", "plan"),
        ("approve", "plan"),
        ("reject", "plan"),
    ],
    "ADMIN": [
        # All permissions
        ("manage", "users"),
        ("manage", "roles"),
        ("manage", "permissions"),
        ("view", "audit"),
        ("manage", "system"),
    ],
}


async def has_permission(
    session: AsyncSession,
    user_id: int,
    permission: str,
    resource: str | None = None,
) -> bool:
    """Check if a user has a specific permission."""
    # Get user role
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        return False

    # Check default permissions for role
    role_permissions = DEFAULT_PERMISSIONS.get(user.role, [])
    for perm, res in role_permissions:
        if perm == permission and (resource is None or res == resource):
            return True

    # Check database for custom permissions
    result = await session.execute(
        select(RolePermission).where(
            RolePermission.role == user.role,
            RolePermission.permission == permission,
        )
    )
    custom_perms = result.scalars().all()

    for perm in custom_perms:
        if perm.permission == permission and (
            resource is None or perm.resource == resource
        ):
            return True

    return False


async def get_user_permissions(
    session: AsyncSession,
    user_id: int,
) -> list[dict[str, Any]]:
    """Get all permissions for a user."""
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        return []

    # Get default permissions
    default_perms = DEFAULT_PERMISSIONS.get(user.role, [])

    # Get custom permissions from database
    result = await session.execute(
        select(RolePermission).where(RolePermission.role == user.role)
    )
    custom_perms = result.scalars().all()

    permissions = []
    for perm, resource in default_perms:
        permissions.append(
            {
                "permission": perm,
                "resource": resource,
                "source": "default",
            }
        )

    for perm in custom_perms:
        permissions.append(
            {
                "permission": perm.permission,
                "resource": perm.resource,
                "source": "custom",
                "description": perm.description,
            }
        )

    return permissions


async def is_officer(session: AsyncSession, user_id: int) -> bool:
    """Check if user is an officer or higher."""
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        return False

    return user.role in {"OFFICER", "REVIEWER", "ADMIN"}


async def is_reviewer(session: AsyncSession, user_id: int) -> bool:
    """Check if user is a reviewer or admin."""
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        return False

    return user.role in {"REVIEWER", "ADMIN"}


async def is_admin(session: AsyncSession, user_id: int) -> bool:
    """Check if user is an admin."""
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        return False

    return user.role == "ADMIN"


def require_role(*allowed_roles: str):
    """Decorator to require specific role."""

    def decorator(func):
        async def wrapper(*args, **kwargs):
            # This would be used with FastAPI Depends
            # Implementation will be in middleware
            return await func(*args, **kwargs)

        return wrapper

    return decorator
