from dataclasses import dataclass
from typing import Callable

from fastapi import Depends, Header, HTTPException, status

from app.core.constants import UserRole


@dataclass(frozen=True)
class CurrentUser:
    """Current authenticated user context from mock headers."""

    user_id: str
    role: str


def get_current_user(
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    x_user_role: str | None = Header(default=None, alias="X-User-Role"),
) -> CurrentUser:
    """Read mock authentication context from request headers."""
    if not x_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-User-Id header.",
        )

    if not x_user_role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-User-Role header.",
        )

    allowed_roles = {role.value for role in UserRole}

    if x_user_role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid user role.",
        )

    return CurrentUser(
        user_id=x_user_id,
        role=x_user_role,
    )


def require_roles(*allowed_roles: UserRole) -> Callable:
    """Create a FastAPI dependency requiring one of the allowed roles."""

    def dependency(
        current_user: CurrentUser = Depends(get_current_user),
    ) -> CurrentUser:
        allowed = {role.value for role in allowed_roles}

        if current_user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions.",
            )

        return current_user

    return dependency