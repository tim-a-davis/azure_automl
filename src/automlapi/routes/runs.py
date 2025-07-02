from fastapi import APIRouter, Depends
from ..services.automl import AzureAutoMLService
from ..schemas.run import Run
from ..auth import get_current_user

router = APIRouter()
service = AzureAutoMLService()

@router.get("/runs", response_model=list[Run])
async def list_runs(user=Depends(get_current_user)):
    return service.list_runs()
from fastapi import WebSocket

@router.websocket("/ws/runs/{run_id}/status")
async def ws_run_status(websocket: WebSocket, run_id: str):
    await websocket.accept()
    await websocket.send_text("running")
