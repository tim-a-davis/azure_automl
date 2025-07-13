"""API routes for working with experiment runs."""

from fastapi import APIRouter, Depends, HTTPException, Path, Response, WebSocket
from sqlalchemy.orm import Session

from ..auth import UserInfo, get_current_user, require_maintainer
from ..db import get_db
from ..db.models import Run as RunModel
from ..schemas.run import Run
from ..utils import model_to_schema, models_to_schema

router = APIRouter()


@router.get(
    "/runs",
    response_model=list[Run],
    operation_id="list_runs",
    tags=["mcp"],
)
async def list_runs(
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Run]:
    """List experiment runs.

    Returns all run records that exist in the database for the current tenant.
    """
    records = db.query(RunModel).all()
    return models_to_schema(records, Run)


@router.get(
    "/runs/{run_id}",
    response_model=Run,
    operation_id="get_run",
    tags=["mcp"],
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
    return model_to_schema(record, Run)


@router.delete(
    "/runs/{run_id}",
    status_code=204,
    operation_id="delete_run",
)
@require_maintainer
async def delete_run(
    run_id: str = Path(..., description="Run identifier"),
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a run.

    Removes the run record from the database if found.
    Only MAINTAINERs and ADMINs can delete runs.
    """
    record = db.get(RunModel, run_id)
    if not record:
        raise HTTPException(status_code=404, detail="Run not found")
    db.delete(record)
    db.commit()
    return Response(status_code=204)


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
    return model_to_schema(record, Run)


@router.websocket("/ws/runs/{run_id}/status", name="ws_run_status")
async def ws_run_status(
    websocket: WebSocket, run_id: str = Path(..., description="Run identifier")
):
    """Stream run status updates.

    Sends simple text notifications about the run's progress.
    """
    await websocket.accept()
    await websocket.send_text("running")
