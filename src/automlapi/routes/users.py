"""API routes for managing users and roles."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..db import get_db
from ..db.models import Role as RoleModel
from ..db.models import User as UserModel
from ..schemas.user import Role, User

router = APIRouter()


@router.post(
    "/users",
    response_model=User,
    operation_id="create_user",
)
async def create_user(
    user: User,
    current=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    """Create a user entry.

    Stores the provided user information in the database.
    """
    record = UserModel(id=user.id, tenant_id=user.tenant_id, role_id=user.role_id)
    db.add(record)
    db.commit()
    db.refresh(record)
    return User(**record.__dict__)


@router.get(
    "/users",
    response_model=list[User],
    operation_id="list_users",
    tags=["mcp"],
)
async def list_users(
    current=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[User]:
    """List users in the system.

    Returns every user record from the database.
    """
    records = db.query(UserModel).all()
    return [User(**r.__dict__) for r in records]


@router.post(
    "/roles",
    response_model=Role,
    operation_id="create_role",
)
async def create_role(
    role: Role,
    current=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Role:
    """Create a user role.

    Adds a new role that can be assigned to users.
    """
    record = RoleModel(id=role.id, name=role.name)
    db.add(record)
    db.commit()
    db.refresh(record)
    return Role(**record.__dict__)
