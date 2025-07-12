from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class Model(BaseModel):
    id: UUID
    tenant_id: str
    dataset_id: Optional[UUID] = Field(default=None, description="Dataset used to train this model")
    task_type: Optional[str] = None
    input_schema: Optional[Dict[str, Any]] = Field(
        default=None, description="Input schema definition"
    )
    output_schema: Optional[Dict[str, Any]] = Field(
        default=None, description="Output schema definition"
    )
    azure_model_id: Optional[str] = None
