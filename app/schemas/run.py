from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Any

class Run(BaseModel):
    id: UUID
    tenant_id: str
    experiment_id: UUID | None = None
    job_name: str | None = None
    queued_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    metrics: Any | None = None
    logs_uri: str | None = None
    charts_uri: str | None = None
    best_model_id: UUID | None = None
