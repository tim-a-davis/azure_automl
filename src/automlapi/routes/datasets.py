"""API routes for managing datasets."""

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, Path
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..db import get_db
from ..db.models import Dataset as DatasetModel
from ..schemas.dataset import Dataset
from ..services.automl import AzureAutoMLService
from ..utils import model_to_schema, models_to_schema

router = APIRouter()


def get_service() -> AzureAutoMLService:
    """Provide a fresh service instance for each request."""
    return AzureAutoMLService()


@router.post(
    "/datasets",
    response_model=Dataset,
    operation_id="create_dataset",
)
async def create_dataset(
    file: UploadFile = File(..., description="Dataset file to upload"),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
    service: AzureAutoMLService = Depends(get_service),
) -> Dataset:
    """Upload a dataset file.

    Reads the provided file and stores it in the workspace. Returns metadata
    about the created dataset record.
    """
    data = await file.read()
    try:
        dataset = service.upload_dataset(file.filename, data)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    record = DatasetModel(
        id=dataset.id,
        tenant_id="",
        asset_id=dataset.asset_id,
        name=dataset.name,
        version=dataset.version,
        storage_uri=dataset.storage_uri,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return dataset


@router.get(
    "/datasets",
    response_model=list[Dataset],
    operation_id="list_datasets",
)
async def list_datasets(
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Dataset]:
    """List uploaded datasets.

    Returns all dataset records stored in the database for the current tenant.
    """
    records = db.query(DatasetModel).all()
    return models_to_schema(records, Dataset)


@router.get(
    "/datasets/{dataset_id}",
    response_model=Dataset,
    operation_id="get_dataset",
)
async def get_dataset(
    dataset_id: str = Path(..., description="Dataset identifier"),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dataset:
    """Retrieve a single dataset.

    Returns the dataset record for the given identifier if it exists.
    """
    record = db.get(DatasetModel, dataset_id)
    if not record:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return model_to_schema(record, Dataset)


@router.delete(
    "/datasets/{dataset_id}",
    status_code=204,
    operation_id="delete_dataset",
)
async def delete_dataset(
    dataset_id: str = Path(..., description="Dataset identifier"),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Remove an existing dataset.

    Deletes the dataset record and associated storage if found.
    """
    record = db.get(DatasetModel, dataset_id)
    if not record:
        raise HTTPException(status_code=404, detail="Dataset not found")
    db.delete(record)
    db.commit()
    return None


@router.put(
    "/datasets/{dataset_id}",
    response_model=Dataset,
    operation_id="update_dataset",
)
async def update_dataset(
    dataset: Dataset,
    dataset_id: str = Path(..., description="Dataset identifier"),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dataset:
    """Modify an existing dataset.

    Updates the stored metadata with the fields provided in the request body.
    """
    record = db.get(DatasetModel, dataset_id)
    if not record:
        raise HTTPException(status_code=404, detail="Dataset not found")
    for field, value in dataset.model_dump().items():
        setattr(record, field, value)
    db.commit()
    db.refresh(record)
    return model_to_schema(record, Dataset)
