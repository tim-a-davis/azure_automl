from pydantic import BaseModel
from uuid import UUID
from typing import Any

class Endpoint(BaseModel):
    id: UUID
    tenant_id: str
    deployments: Any | None = None
    blue_traffic: int | None = None
    latency: float | None = None
    error_rate: float | None = None
