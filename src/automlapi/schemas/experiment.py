from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class Experiment(BaseModel):
    id: UUID
    tenant_id: str
    task_type: str | None = None
    primary_metric: str | None = None
    training_data: str | None = None
    target_column_name: str | None = None
    compute: str | None = None
    n_cross_validations: int | None = None

    # Limit settings with defaults
    enable_early_termination: Optional[bool] = None
    exit_score: Optional[float] = None
    max_concurrent_trials: Optional[int] = 20
    max_cores_per_trial: Optional[int] = None
    max_nodes: Optional[int] = 10
    max_trials: Optional[int] = 300
    timeout_minutes: Optional[int] = None
    trial_timeout_minutes: Optional[int] = 15
