"""API routes for running AutoML experiments."""

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session

from ..services.automl import AzureAutoMLService
from ..utils import model_to_schema, models_to_schema
from ..schemas.experiment import Experiment
from ..schemas.run import Run
from ..auth import get_current_user
from ..db import get_db
from ..db.models import Experiment as ExperimentModel, Run as RunModel

router = APIRouter()


def get_service() -> AzureAutoMLService:
    """Provide a fresh service instance for each request."""
    return AzureAutoMLService()

@router.post(
    "/experiments",
    response_model=Run,
    operation_id="start_experiment",
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
        dataset_id=None,
        task_type=exp.task_type,
        primary_metric=exp.primary_metric,
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
)
async def list_experiments(
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Experiment]:
    """List AutoML experiments.

    Returns all experiments that have been recorded in the database.
    """
    records = db.query(ExperimentModel).all()
    return models_to_schema(records, Experiment)


@router.get(
    "/experiments/{experiment_id}",
    response_model=Experiment,
    operation_id="get_experiment",
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
    return model_to_schema(record, Experiment)


@router.delete(
    "/experiments/{experiment_id}",
    status_code=204,
    operation_id="delete_experiment",
)
async def delete_experiment(
    experiment_id: str = Path(..., description="Experiment identifier"),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Delete an experiment.

    Removes the experiment record from the database if it exists.
    """
    record = db.get(ExperimentModel, experiment_id)
    if not record:
        raise HTTPException(status_code=404, detail="Experiment not found")
    db.delete(record)
    db.commit()
    return None


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
