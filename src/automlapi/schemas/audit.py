from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class AuditEntry(BaseModel):
    id: UUID
    tenant_id: str
    user_id: Optional[UUID] = None
    action: Optional[str] = None
    timestamp: Optional[datetime] = None
    diff: Optional[Dict[str, Any]] = Field(default=None, description="Changes made")
