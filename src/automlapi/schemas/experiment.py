from pydantic import BaseModel
from uuid import UUID

class Experiment(BaseModel):
    id: UUID
    tenant_id: str
    task_type: str | None = None
    primary_metric: str | None = None
    training_data: str | None = None
    target_column_name: str | None = None
    compute: str | None = None
    n_cross_validations: int | None = None
