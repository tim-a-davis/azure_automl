"""API routes for managing users and roles."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import UserInfo, get_current_user, require_admin
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
@require_admin
async def create_user(
    user: User,
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    """Create a user entry.

    Stores the provided user information in the database.
    Only ADMINs can create users.
    """
    # Verify the role_id exists if provided
    if user.role_id:
        role_exists = db.query(RoleModel).filter(RoleModel.id == user.role_id).first()
        if not role_exists:
            raise HTTPException(status_code=400, detail="Invalid role_id")

    record = UserModel(id=user.id, role_id=user.role_id)
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
    current_user: UserInfo = Depends(get_current_user),
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
@require_admin
async def create_role(
    role: Role,
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Role:
    """Create a user role.

    Adds a new role that can be assigned to users.
    Only ADMINs can create roles.
    """
    # Check if role name already exists
    existing_role = db.query(RoleModel).filter(RoleModel.name == role.name).first()
    if existing_role:
        raise HTTPException(status_code=400, detail="Role name already exists")

    record = RoleModel(id=role.id, name=role.name)
    db.add(record)
    db.commit()
    db.refresh(record)
    return Role(**record.__dict__)


@router.get(
    "/roles",
    response_model=list[Role],
    operation_id="list_roles",
)
async def list_roles(
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Role]:
    """List all available roles.

    Returns all role records from the database.
    """
    records = db.query(RoleModel).all()
    return [Role(**r.__dict__) for r in records]


@router.delete(
    "/users/{user_id}",
    operation_id="delete_user",
)
@require_admin
async def delete_user(
    user_id: str,
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Delete a user.

    Only ADMINs can delete users.
    """
    user_record = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user_record:
        raise HTTPException(status_code=404, detail="User not found")

    db.delete(user_record)
    db.commit()
    return {"message": "User deleted successfully"}


@router.delete(
    "/roles/{role_id}",
    operation_id="delete_role",
)
@require_admin
async def delete_role(
    role_id: str,
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Delete a role.

    Only ADMINs can delete roles.
    """
    role_record = db.query(RoleModel).filter(RoleModel.id == role_id).first()
    if not role_record:
        raise HTTPException(status_code=404, detail="Role not found")

    # Check if any users are assigned this role
    users_with_role = db.query(UserModel).filter(UserModel.role_id == role_id).count()
    if users_with_role > 0:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete role: users are still assigned to this role",
        )

    db.delete(role_record)
    db.commit()
    return {"message": "Role deleted successfully"}
