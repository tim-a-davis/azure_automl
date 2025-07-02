from fastapi import APIRouter, Depends, WebSocket, HTTPException
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..schemas.run import Run
from ..services.automl import AzureAutoMLService
from ..db import get_db
from ..db.models import Run as RunModel

router = APIRouter()
service = AzureAutoMLService()


@router.get("/runs", response_model=list[Run])
async def list_runs(
    user=Depends(get_current_user), db: Session = Depends(get_db)
):
    records = db.query(RunModel).all()
    return [Run(**r.__dict__) for r in records]


@router.get("/runs/{run_id}", response_model=Run)
async def get_run(
    run_id: str,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = db.get(RunModel, run_id)
    if not record:
        raise HTTPException(status_code=404, detail="Run not found")
    return Run(**record.__dict__)


@router.delete("/runs/{run_id}", status_code=204)
async def delete_run(
    run_id: str,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = db.get(RunModel, run_id)
    if not record:
        raise HTTPException(status_code=404, detail="Run not found")
    db.delete(record)
    db.commit()
    return None


@router.put("/runs/{run_id}", response_model=Run)
async def update_run(
    run_id: str,
    run: Run,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = db.get(RunModel, run_id)
    if not record:
        raise HTTPException(status_code=404, detail="Run not found")
    for field, value in run.model_dump().items():
        setattr(record, field, value)
    db.commit()
    db.refresh(record)
    return Run(**record.__dict__)


@router.websocket("/ws/runs/{run_id}/status")
async def ws_run_status(websocket: WebSocket, run_id: str):
    await websocket.accept()
    await websocket.send_text("running")
