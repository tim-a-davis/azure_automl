from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..db import get_db
from ..db.models import User as UserModel, Role as RoleModel
from ..schemas.user import User, Role

router = APIRouter()

@router.post("/users", response_model=User)
async def create_user(user: User, current=Depends(get_current_user), db: Session = Depends(get_db)):
    record = UserModel(id=user.id, tenant_id=user.tenant_id, role_id=user.role_id)
    db.add(record)
    db.commit()
    db.refresh(record)
    return User(**record.__dict__)

@router.get("/users", response_model=list[User])
async def list_users(current=Depends(get_current_user), db: Session = Depends(get_db)):
    records = db.query(UserModel).all()
    return [User(**r.__dict__) for r in records]

@router.post("/roles", response_model=Role)
async def create_role(role: Role, current=Depends(get_current_user), db: Session = Depends(get_db)):
    record = RoleModel(id=role.id, name=role.name)
    db.add(record)
    db.commit()
    db.refresh(record)
    return Role(**record.__dict__)

