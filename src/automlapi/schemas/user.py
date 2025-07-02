from pydantic import BaseModel
from uuid import UUID

class Role(BaseModel):
    id: UUID
    name: str | None = None

class User(BaseModel):
    id: UUID
    tenant_id: str
    role_id: UUID | None = None
