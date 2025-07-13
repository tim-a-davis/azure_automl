"""Authentication utilities used by the API."""

from enum import Enum
from functools import wraps
from typing import Optional

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session

from .config import settings
from .db import get_db
from .db.models import Role as RoleModel
from .db.models import User as UserModel

security = HTTPBearer()


class UserRole(str, Enum):
    """User roles for RBAC."""

    USER = "USER"
    MAINTAINER = "MAINTAINER"
    ADMIN = "ADMIN"


class UserInfo:
    """Information about the current authenticated user."""

    def __init__(self, user_id: str, role: Optional[str] = None):
        self.user_id = user_id
        self.role = role

    def has_role(self, required_role: UserRole) -> bool:
        """Check if user has the required role or higher."""
        role_hierarchy = {UserRole.USER: 1, UserRole.MAINTAINER: 2, UserRole.ADMIN: 3}

        if not self.role:
            return False

        user_level = role_hierarchy.get(UserRole(self.role), 0)
        required_level = role_hierarchy.get(required_role, 0)

        return user_level >= required_level


async def get_current_user(
    token: str = Depends(security), db: Session = Depends(get_db)
) -> UserInfo:
    """Validate the JWT token and return user information with role."""
    try:
        payload = jwt.decode(
            token.credentials, settings.jwt_secret, algorithms=["HS256"]
        )
        user_id = payload.get("sub")

        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")

        # Look up user in database to get role
        user_record = db.query(UserModel).filter(UserModel.id == user_id).first()

        role = None
        if user_record and user_record.role_id:
            role_record = (
                db.query(RoleModel).filter(RoleModel.id == user_record.role_id).first()
            )
            if role_record:
                role = role_record.name

        return UserInfo(user_id=user_id, role=role)

    except Exception:
        raise HTTPException(status_code=403, detail="Authentication failed")


def require_role(required_role: UserRole):
    """Decorator to require a specific role or higher for route access."""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get current user from kwargs
            current_user = None
            for key, value in kwargs.items():
                if isinstance(value, UserInfo):
                    current_user = value
                    break

            if not current_user:
                raise HTTPException(status_code=401, detail="Authentication required")

            if not current_user.has_role(required_role):
                raise HTTPException(
                    status_code=403,
                    detail=f"Insufficient privileges. Required role: {required_role.value} or higher",
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


# Convenience functions for specific role requirements
def require_admin(func):
    """Require ADMIN role for route access."""
    return require_role(UserRole.ADMIN)(func)


def require_maintainer(func):
    """Require MAINTAINER role or higher for route access."""
    return require_role(UserRole.MAINTAINER)(func)


def require_user(func):
    """Require USER role or higher for route access."""
    return require_role(UserRole.USER)(func)
