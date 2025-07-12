from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class Experiment(BaseModel):
    id: UUID
    tenant_id: str
    dataset_id: Optional[UUID] = None  # Link to the dataset used for training
    task_type: Optional[str] = None
    primary_metric: Optional[str] = None
    training_data: Optional[str] = None
    target_column_name: Optional[str] = None
    compute: Optional[str] = None
    n_cross_validations: Optional[int] = None

    # Limit settings with defaults
    enable_early_termination: Optional[bool] = None
    exit_score: Optional[float] = None
    max_concurrent_trials: Optional[int] = 20
    max_cores_per_trial: Optional[int] = None
    max_nodes: Optional[int] = 10
    max_trials: Optional[int] = 300
    timeout_minutes: Optional[int] = None
    trial_timeout_minutes: Optional[int] = 15
