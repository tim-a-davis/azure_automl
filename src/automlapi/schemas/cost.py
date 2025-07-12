from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class CostRecord(BaseModel):
    id: UUID
    tenant_id: str
    billing_scope: Optional[str] = None
    last_bill: Optional[float] = None
