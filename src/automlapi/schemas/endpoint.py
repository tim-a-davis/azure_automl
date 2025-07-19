from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class Endpoint(BaseModel):
    id: UUID
    user_id: UUID  # User who created the endpoint
    name: Optional[str] = Field(
        default=None, description="Display name for the endpoint"
    )
    azure_endpoint_name: Optional[str] = Field(
        default=None, description="Azure ML endpoint name"
    )
    azure_endpoint_url: Optional[str] = Field(
        default=None, description="Azure ML endpoint scoring URL"
    )
    auth_mode: Optional[str] = Field(
        default="key", description="Authentication mode (key or aml_token)"
    )
    provisioning_state: Optional[str] = Field(
        default=None, description="Azure ML provisioning state"
    )
    description: Optional[str] = Field(default=None, description="Endpoint description")
    dataset_id: Optional[UUID] = Field(
        default=None, description="Dataset used for this endpoint"
    )
    deployments: Optional[Dict[str, Any]] = Field(
        default=None, description="Deployment configuration"
    )
    traffic: Optional[Dict[str, int]] = Field(
        default=None, description="Traffic allocation"
    )
    tags: Optional[Dict[str, str]] = Field(default=None, description="Azure ML tags")
    blue_traffic: Optional[int] = None
    latency: Optional[float] = None
    error_rate: Optional[float] = None
