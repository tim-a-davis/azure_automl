from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class Endpoint(BaseModel):
    id: UUID
    tenant_id: str
    deployments: Optional[Dict[str, Any]] = Field(
        default=None, description="Deployment configuration"
    )
    blue_traffic: Optional[int] = None
    latency: Optional[float] = None
    error_rate: Optional[float] = None
