from pydantic import BaseModel
from uuid import UUID

class CostRecord(BaseModel):
    id: UUID
    tenant_id: str
    billing_scope: str | None = None
    last_bill: float | None = None
