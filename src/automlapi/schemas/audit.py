from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Any

class AuditEntry(BaseModel):
    id: UUID
    tenant_id: str
    user_id: UUID | None = None
    action: str | None = None
    timestamp: datetime | None = None
    diff: Any | None = None
