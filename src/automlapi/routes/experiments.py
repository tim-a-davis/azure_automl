"""API routes for running AutoML experiments."""

from fastapi import APIRouter, Depends, HTTPException, Path, Response
from sqlalchemy.orm import Session

from ..auth import UserInfo, get_current_user, require_maintainer
from ..db import get_db
from ..db.models import Experiment as ExperimentModel
from ..db.models import Run as RunModel
from ..schemas.experiment import Experiment
from ..schemas.run import Run
from ..services.automl import AzureAutoMLService
from ..utils import model_to_schema

router = APIRouter()


def get_service() -> AzureAutoMLService:
    """Provide a fresh service instance for each request."""
    return AzureAutoMLService()


@router.post(
    "/experiments",
    response_model=Run,
    operation_id="start_experiment",
    tags=["mcp"],
)
async def start_experiment(
    exp: Experiment,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
    service: AzureAutoMLService = Depends(get_service),
) -> Run:
    """Start a new AutoML experiment.

    Creates a job in Azure ML and records the experiment and run information in
    the database.
    """
    run = service.start_experiment(exp)
    exp_record = ExperimentModel(
        id=exp.id,
        tenant_id=exp.tenant_id,
        dataset_id=exp.dataset_id,
        task_type=exp.task_type,
        primary_metric=exp.primary_metric,
        enable_early_termination=str(exp.enable_early_termination).lower()
        if exp.enable_early_termination is not None
        else None,
        exit_score=exp.exit_score,
        max_concurrent_trials=exp.max_concurrent_trials,
        max_cores_per_trial=exp.max_cores_per_trial,
        max_nodes=exp.max_nodes,
        max_trials=exp.max_trials,
        timeout_minutes=exp.timeout_minutes,
        trial_timeout_minutes=exp.trial_timeout_minutes,
    )
    db.add(exp_record)
    db.add(
        RunModel(
            id=run.id,
            tenant_id=run.tenant_id,
            experiment_id=exp.id,
            job_name=run.job_name,
            queued_at=run.queued_at,
        )
    )
    db.commit()
    return run


@router.get(
    "/experiments",
    response_model=list[Experiment],
    operation_id="list_experiments",
    tags=["mcp"],
)
async def list_experiments(
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Experiment]:
    """List AutoML experiments.

    Returns all experiments that have been recorded in the database.
    """
    records = db.query(ExperimentModel).all()
    return experiment_models_to_schema(records)


@router.get(
    "/experiments/{experiment_id}",
    response_model=Experiment,
    operation_id="get_experiment",
    tags=["mcp"],
)
async def get_experiment(
    experiment_id: str = Path(..., description="Experiment identifier"),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Experiment:
    """Retrieve an experiment.

    Returns details about a specific experiment by its ID.
    """
    record = db.get(ExperimentModel, experiment_id)
    if not record:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return experiment_model_to_schema(record)


@router.delete(
    "/experiments/{experiment_id}",
    status_code=204,
    operation_id="delete_experiment",
)
@require_maintainer
async def delete_experiment(
    experiment_id: str = Path(..., description="Experiment identifier"),
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete an experiment.

    Removes the experiment record from the database if it exists.
    Only MAINTAINERs and ADMINs can delete experiments.
    """
    record = db.get(ExperimentModel, experiment_id)
    if not record:
        raise HTTPException(status_code=404, detail="Experiment not found")
    db.delete(record)
    db.commit()
    return Response(status_code=204)


@router.put(
    "/experiments/{experiment_id}",
    response_model=Experiment,
    operation_id="update_experiment",
)
async def update_experiment(
    exp: Experiment,
    experiment_id: str = Path(..., description="Experiment identifier"),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
    tags=["mcp"],
) -> Experiment:
    """Update an experiment record.

    Overwrites stored experiment metadata with the new values provided.
    """
    record = db.get(ExperimentModel, experiment_id)
    if not record:
        raise HTTPException(status_code=404, detail="Experiment not found")
    for field, value in exp.model_dump().items():
        setattr(record, field, value)
    db.commit()
    db.refresh(record)
    return model_to_schema(record, Experiment)


def experiment_model_to_schema(model: ExperimentModel) -> Experiment:
    """Convert ExperimentModel to Experiment schema with proper boolean conversion."""
    # Convert the model to dict first
    model_dict = {
        "id": model.id,
        "tenant_id": model.tenant_id,
        "task_type": model.task_type,
        "primary_metric": model.primary_metric,
        "training_data": None,  # This field doesn't exist in the model
        "target_column_name": None,  # This field doesn't exist in the model
        "compute": None,  # This field doesn't exist in the model
        "n_cross_validations": None,  # This field doesn't exist in the model
        "enable_early_termination": model.enable_early_termination == "true"
        if model.enable_early_termination
        else None,
        "exit_score": model.exit_score,
        "max_concurrent_trials": model.max_concurrent_trials,
        "max_cores_per_trial": model.max_cores_per_trial,
        "max_nodes": model.max_nodes,
        "max_trials": model.max_trials,
        "timeout_minutes": model.timeout_minutes,
        "trial_timeout_minutes": model.trial_timeout_minutes,
    }
    return Experiment(**model_dict)


def experiment_models_to_schema(models: list[ExperimentModel]) -> list[Experiment]:
    """Convert list of ExperimentModel to list of Experiment schemas."""
    return [experiment_model_to_schema(m) for m in models]
