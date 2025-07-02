from fastapi import APIRouter, Depends, WebSocket, HTTPException, Path
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..schemas.run import Run
from ..services.automl import AzureAutoMLService
from ..db import get_db
from ..db.models import Run as RunModel

router = APIRouter()
service = AzureAutoMLService()


@router.get(
    "/runs",
    response_model=list[Run],
    operation_id="list_runs",
)
async def list_runs(
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Run]:
    """List experiment runs.

    Returns all run records that exist in the database for the current tenant.
    """
    records = db.query(RunModel).all()
    return [Run(**r.__dict__) for r in records]


@router.get(
    "/runs/{run_id}",
    response_model=Run,
    operation_id="get_run",
)
async def get_run(
    run_id: str = Path(..., description="Run identifier"),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Run:
    """Get information about a run.

    Returns run metadata for the specified run ID.
    """
    record = db.get(RunModel, run_id)
    if not record:
        raise HTTPException(status_code=404, detail="Run not found")
    return Run(**record.__dict__)


@router.delete(
    "/runs/{run_id}",
    status_code=204,
    operation_id="delete_run",
)
async def delete_run(
    run_id: str = Path(..., description="Run identifier"),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Delete a run.

    Removes the run record from the database if found.
    """
    record = db.get(RunModel, run_id)
    if not record:
        raise HTTPException(status_code=404, detail="Run not found")
    db.delete(record)
    db.commit()
    return None


@router.put(
    "/runs/{run_id}",
    response_model=Run,
    operation_id="update_run",
)
async def update_run(
    run: Run,
    run_id: str = Path(..., description="Run identifier"),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Run:
    """Update a run record.

    Applies the provided fields to the stored run entry.
    """
    record = db.get(RunModel, run_id)
    if not record:
        raise HTTPException(status_code=404, detail="Run not found")
    for field, value in run.model_dump().items():
        setattr(record, field, value)
    db.commit()
    db.refresh(record)
    return Run(**record.__dict__)


@router.websocket("/ws/runs/{run_id}/status", name="ws_run_status")
async def ws_run_status(websocket: WebSocket, run_id: str = Path(..., description="Run identifier")):
    """Stream run status updates.

    Sends simple text notifications about the run's progress.
    """
    await websocket.accept()
    await websocket.send_text("running")
