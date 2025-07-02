from pydantic import BaseModel
from uuid import UUID

class Experiment(BaseModel):
    id: UUID
    tenant_id: str
    task_type: str | None = None
    primary_metric: str | None = None
