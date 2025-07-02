from fastapi import APIRouter, Depends, WebSocket, HTTPException
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..schemas.endpoint import Endpoint
from ..services.automl import AzureAutoMLService
from ..db import get_db
from ..db.models import Endpoint as EndpointModel

router = APIRouter()
service = AzureAutoMLService()


@router.post("/endpoints", response_model=Endpoint)
async def create_endpoint(
    endpoint: Endpoint,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = EndpointModel(**endpoint.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return Endpoint(**record.__dict__)


@router.get("/endpoints", response_model=list[Endpoint])
async def list_endpoints(
    user=Depends(get_current_user), db: Session = Depends(get_db)
):
    records = db.query(EndpointModel).all()
    return [Endpoint(**r.__dict__) for r in records]


@router.get("/endpoints/{endpoint_id}", response_model=Endpoint)
async def get_endpoint(
    endpoint_id: str,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = db.get(EndpointModel, endpoint_id)
    if not record:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    return Endpoint(**record.__dict__)


@router.delete("/endpoints/{endpoint_id}", status_code=204)
async def delete_endpoint(
    endpoint_id: str,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = db.get(EndpointModel, endpoint_id)
    if not record:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    db.delete(record)
    db.commit()
    return None


@router.put("/endpoints/{endpoint_id}", response_model=Endpoint)
async def update_endpoint(
    endpoint_id: str,
    endpoint: Endpoint,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = db.get(EndpointModel, endpoint_id)
    if not record:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    for field, value in endpoint.model_dump().items():
        setattr(record, field, value)
    db.commit()
    db.refresh(record)
    return Endpoint(**record.__dict__)


@router.websocket("/ws/endpoints/{endpoint_id}/traffic")
async def ws_endpoint_traffic(websocket: WebSocket, endpoint_id: str):
    await websocket.accept()
    await websocket.send_text("0")
