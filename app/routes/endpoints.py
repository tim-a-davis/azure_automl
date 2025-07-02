from fastapi import APIRouter, Depends
from ..services.automl import AzureAutoMLService
from ..schemas.endpoint import Endpoint
from ..auth import get_current_user

router = APIRouter()
service = AzureAutoMLService()

@router.get("/endpoints", response_model=list[Endpoint])
async def list_endpoints(user=Depends(get_current_user)):
    return service.list_endpoints()
from fastapi import WebSocket

@router.websocket("/ws/endpoints/{endpoint_id}/traffic")
async def ws_endpoint_traffic(websocket: WebSocket, endpoint_id: str):
    await websocket.accept()
    await websocket.send_text("0")
