from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session

from ..services.automl import AzureAutoMLService
from ..schemas.model import Model
from ..auth import get_current_user
from ..db import get_db
from ..db.models import Model as ModelModel

router = APIRouter()
service = AzureAutoMLService()

@router.post(
    "/models",
    response_model=Model,
    operation_id="create_model",
)
async def create_model(
    model: Model,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Model:
    """Register a model.

    Saves the provided model metadata to the database.
    """
    record = ModelModel(**model.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return Model(**record.__dict__)


@router.get(
    "/models",
    response_model=list[Model],
    operation_id="list_models",
)
async def list_models(
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Model]:
    """List registered models.

    Returns metadata for all stored model records.
    """
    records = db.query(ModelModel).all()
    return [Model(**r.__dict__) for r in records]


@router.get(
    "/models/{model_id}",
    response_model=Model,
    operation_id="get_model",
)
async def get_model(
    model_id: str = Path(..., description="Model identifier"),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Model:
    """Retrieve a model by ID.

    Returns model metadata if the requested record exists.
    """
    record = db.get(ModelModel, model_id)
    if not record:
        raise HTTPException(status_code=404, detail="Model not found")
    return Model(**record.__dict__)


@router.delete(
    "/models/{model_id}",
    status_code=204,
    operation_id="delete_model",
)
async def delete_model(
    model_id: str = Path(..., description="Model identifier"),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Delete a model record.

    Removes the specified model from the database.
    """
    record = db.get(ModelModel, model_id)
    if not record:
        raise HTTPException(status_code=404, detail="Model not found")
    db.delete(record)
    db.commit()
    return None


@router.put(
    "/models/{model_id}",
    response_model=Model,
    operation_id="update_model",
)
async def update_model(
    model: Model,
    model_id: str = Path(..., description="Model identifier"),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Model:
    """Update a model.

    Applies changes to the stored model metadata.
    """
    record = db.get(ModelModel, model_id)
    if not record:
        raise HTTPException(status_code=404, detail="Model not found")
    for field, value in model.model_dump().items():
        setattr(record, field, value)
    db.commit()
    db.refresh(record)
    return Model(**record.__dict__)
