from pydantic import BaseModel
from uuid import UUID
from typing import Any

class Model(BaseModel):
    id: UUID
    tenant_id: str
    task_type: str | None = None
    input_schema: Any | None = None
    output_schema: Any | None = None
    azure_model_id: str | None = None
