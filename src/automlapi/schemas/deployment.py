from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class Deployment(BaseModel):
    id: UUID
    user_id: UUID = Field(description="User who created the deployment")
    endpoint_id: UUID = Field(description="Endpoint this deployment belongs to")
    model_id: UUID = Field(description="Model being deployed")
    deployment_name: str = Field(description="Name of the deployment")
    azure_deployment_name: Optional[str] = Field(
        default=None, description="Azure ML deployment name"
    )
    instance_type: str = Field(
        default="Standard_DS3_v2", description="Azure instance type"
    )
    instance_count: int = Field(default=1, description="Number of instances")
    traffic_percentage: int = Field(
        default=100, description="Percentage of traffic (0-100)"
    )
    deployment_status: str = Field(default="creating", description="Deployment status")
    provisioning_state: Optional[str] = Field(
        default=None, description="Azure ML provisioning state"
    )
    deployment_config: Optional[Dict[str, Any]] = Field(
        default=None, description="Full deployment configuration"
    )
    error_message: Optional[str] = Field(
        default=None, description="Error message if deployment failed"
    )
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class DeploymentCreate(BaseModel):
    endpoint_id: UUID
    model_id: UUID
    deployment_name: str
    instance_type: str = Field(default="Standard_DS3_v2")
    instance_count: int = Field(default=1)
    traffic_percentage: int = Field(default=100)


class DeploymentRequest(BaseModel):
    experiment_id: Optional[UUID] = Field(
        default=None, description="Experiment ID (use latest run if not specified)"
    )
    run_id: Optional[UUID] = Field(
        default=None, description="Specific run ID to deploy"
    )
    endpoint_name: str = Field(description="Name for the endpoint")
    deployment_name: Optional[str] = Field(
        default=None,
        description="Name for the deployment (auto-generated if not provided)",
    )
    instance_type: str = Field(
        default="Standard_DS3_v2", description="Azure instance type"
    )
    instance_count: int = Field(default=1, description="Number of instances")
    traffic_percentage: int = Field(
        default=100, description="Initial traffic percentage"
    )
    stream_logs: bool = Field(
        default=False, description="Whether to stream deployment logs"
    )


class DeploymentResponse(BaseModel):
    deployment_id: UUID
    model_id: UUID
    endpoint_id: UUID
    endpoint_url: Optional[str] = None
    deployment_status: str
    message: str
    task_id: Optional[str] = Field(
        default=None, description="Background task ID for async deployments"
    )
