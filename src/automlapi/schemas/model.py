from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class Model(BaseModel):
    id: UUID
    user_id: UUID = Field(description="User who registered the model")
    dataset_id: Optional[UUID] = Field(
        default=None, description="Dataset used to train this model"
    )
    experiment_id: Optional[UUID] = Field(
        default=None, description="Experiment that created this model"
    )
    run_id: Optional[UUID] = Field(
        default=None, description="Run that created this model"
    )
    task_type: Optional[str] = None
    algorithm: Optional[str] = Field(default=None, description="ML algorithm used")
    azure_model_name: Optional[str] = Field(
        default=None, description="Name in Azure ML registry"
    )
    azure_model_version: Optional[str] = Field(
        default=None, description="Version in Azure ML"
    )
    model_uri: Optional[str] = Field(
        default=None, description="Full Azure ML model URI"
    )
    best_score: Optional[float] = Field(
        default=None, description="Primary metric score"
    )
    performance_metrics: Optional[Dict[str, Any]] = Field(
        default=None, description="All performance metrics"
    )
    model_metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Comprehensive model metadata"
    )
    input_schema: Optional[Dict[str, Any]] = Field(
        default=None, description="Input schema definition"
    )
    output_schema: Optional[Dict[str, Any]] = Field(
        default=None, description="Output schema definition"
    )
    registration_status: Optional[str] = Field(
        default="pending", description="Registration status"
    )
    error_message: Optional[str] = Field(
        default=None, description="Error message if registration failed"
    )
    # Keep existing field for backward compatibility
    azure_model_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ModelCreate(BaseModel):
    dataset_id: Optional[UUID] = None
    experiment_id: Optional[UUID] = None
    run_id: Optional[UUID] = None
    task_type: Optional[str] = None
    algorithm: Optional[str] = None
    azure_model_name: Optional[str] = None
    azure_model_version: Optional[str] = None
    model_uri: Optional[str] = None
    best_score: Optional[float] = None
    performance_metrics: Optional[Dict[str, Any]] = None
    model_metadata: Optional[Dict[str, Any]] = None
    input_schema: Optional[Dict[str, Any]] = None
    output_schema: Optional[Dict[str, Any]] = None
