from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class Role(BaseModel):
    id: UUID
    name: Optional[str] = None


class User(BaseModel):
    id: UUID
    tenant_id: str
    role_id: Optional[UUID] = None
