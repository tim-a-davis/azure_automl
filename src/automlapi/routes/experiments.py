from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..services.automl import AzureAutoMLService
from ..schemas.experiment import Experiment
from ..schemas.run import Run
from ..auth import get_current_user
from ..db import get_db
from ..db.models import Experiment as ExperimentModel, Run as RunModel

router = APIRouter()
service = AzureAutoMLService()

@router.post("/experiments", response_model=Run)
async def start_experiment(
    exp: Experiment,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
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

@router.get("/experiments", response_model=list[Experiment])
async def list_experiments(
    user=Depends(get_current_user), db: Session = Depends(get_db)
):
    records = db.query(ExperimentModel).all()
    return [Experiment(**r.__dict__) for r in records]


@router.get("/experiments/{experiment_id}", response_model=Experiment)
async def get_experiment(
    experiment_id: str,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = db.get(ExperimentModel, experiment_id)
    if not record:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return Experiment(**record.__dict__)


@router.delete("/experiments/{experiment_id}", status_code=204)
async def delete_experiment(
    experiment_id: str,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = db.get(ExperimentModel, experiment_id)
    if not record:
        raise HTTPException(status_code=404, detail="Experiment not found")
    db.delete(record)
    db.commit()
    return None


@router.put("/experiments/{experiment_id}", response_model=Experiment)
async def update_experiment(
    experiment_id: str,
    exp: Experiment,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = db.get(ExperimentModel, experiment_id)
    if not record:
        raise HTTPException(status_code=404, detail="Experiment not found")
    for field, value in exp.model_dump().items():
        setattr(record, field, value)
    db.commit()
    db.refresh(record)
    return Experiment(**record.__dict__)
