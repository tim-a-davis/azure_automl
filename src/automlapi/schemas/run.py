from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class Run(BaseModel):
    id: UUID
    user_id: Optional[UUID] = None  # Will be set by the server from authenticated user
    experiment_id: Optional[UUID] = None
    job_name: Optional[str] = None
    queued_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metrics: Optional[Dict[str, Any]] = Field(
        default=None, description="Training metrics"
    )
    logs_uri: Optional[str] = None
    charts_uri: Optional[str] = None
    best_model_id: Optional[UUID] = None
