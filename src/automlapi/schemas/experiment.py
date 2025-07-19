from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class Experiment(BaseModel):
    """Azure AutoML experiment configuration schema."""

    id: UUID = Field(description="Unique identifier linked to Azure ML experiment")
    user_id: Optional[UUID] = Field(
        None, description="User ID set by server from authenticated user"
    )
    dataset_id: Optional[UUID] = Field(
        None, description="Reference to dataset used for training"
    )
    task_type: Optional[str] = Field(
        None, description="ML task type (classification, regression, forecasting)"
    )
    primary_metric: Optional[str] = Field(
        None, description="Primary metric for model evaluation"
    )
    training_data: Optional[str] = Field(
        None, description="Path or reference to training data"
    )
    target_column_name: Optional[str] = Field(
        None, description="Name of target column to predict"
    )
    compute: Optional[str] = Field(None, description="Azure ML compute target name")
    n_cross_validations: Optional[int] = Field(
        None, description="Number of cross-validation folds"
    )

    # Limit settings with defaults
    enable_early_termination: Optional[bool] = Field(
        None, description="Enable early termination of poor performing trials"
    )
    exit_score: Optional[float] = Field(
        None, description="Target metric score to stop training when reached"
    )
    max_concurrent_trials: Optional[int] = Field(
        20, description="Maximum number of trials to run concurrently"
    )
    max_cores_per_trial: Optional[int] = Field(
        None, description="Maximum CPU cores per trial"
    )
    max_nodes: Optional[int] = Field(10, description="Maximum number of compute nodes")
    max_trials: Optional[int] = Field(
        300, description="Maximum total number of trials to run"
    )
    timeout_minutes: Optional[int] = Field(
        None, description="Total experiment timeout in minutes"
    )
    trial_timeout_minutes: Optional[int] = Field(
        15, description="Individual trial timeout in minutes"
    )
