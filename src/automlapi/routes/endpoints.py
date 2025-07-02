from fastapi import APIRouter, Depends, WebSocket, HTTPException, Path
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..schemas.endpoint import Endpoint
from ..services.automl import AzureAutoMLService
from ..db import get_db
from ..db.models import Endpoint as EndpointModel

router = APIRouter()
service = AzureAutoMLService()


@router.post(
    "/endpoints",
    response_model=Endpoint,
    operation_id="create_endpoint",
)
async def create_endpoint(
    endpoint: Endpoint,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Endpoint:
    """Create a deployment endpoint.

    Persists the endpoint configuration and returns the stored record.
    """
    record = EndpointModel(**endpoint.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return Endpoint(**record.__dict__)


@router.get(
    "/endpoints",
    response_model=list[Endpoint],
    operation_id="list_endpoints",
)
async def list_endpoints(
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Endpoint]:
    """List deployment endpoints.

    Returns all endpoint records stored in the database.
    """
    records = db.query(EndpointModel).all()
    return [Endpoint(**r.__dict__) for r in records]


@router.get(
    "/endpoints/{endpoint_id}",
    response_model=Endpoint,
    operation_id="get_endpoint",
)
async def get_endpoint(
    endpoint_id: str = Path(..., description="Endpoint identifier"),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Endpoint:
    """Fetch an endpoint by ID.

    Returns the stored endpoint record if present.
    """
    record = db.get(EndpointModel, endpoint_id)
    if not record:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    return Endpoint(**record.__dict__)


@router.delete(
    "/endpoints/{endpoint_id}",
    status_code=204,
    operation_id="delete_endpoint",
)
async def delete_endpoint(
    endpoint_id: str = Path(..., description="Endpoint identifier"),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Remove a deployment endpoint.

    Deletes the record from the database if found.
    """
    record = db.get(EndpointModel, endpoint_id)
    if not record:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    db.delete(record)
    db.commit()
    return None


@router.put(
    "/endpoints/{endpoint_id}",
    response_model=Endpoint,
    operation_id="update_endpoint",
)
async def update_endpoint(
    endpoint: Endpoint,
    endpoint_id: str = Path(..., description="Endpoint identifier"),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Endpoint:
    """Update an endpoint record.

    Applies the provided fields to the stored endpoint metadata.
    """
    record = db.get(EndpointModel, endpoint_id)
    if not record:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    for field, value in endpoint.model_dump().items():
        setattr(record, field, value)
    db.commit()
    db.refresh(record)
    return Endpoint(**record.__dict__)


@router.websocket("/ws/endpoints/{endpoint_id}/traffic", name="ws_endpoint_traffic")
async def ws_endpoint_traffic(
    websocket: WebSocket,
    endpoint_id: str = Path(..., description="Endpoint identifier"),
):
    """Stream endpoint traffic metrics.

    Sends basic traffic statistics for the specified endpoint.
    """
    await websocket.accept()
    await websocket.send_text("0")
