from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..db import get_db
from ..db.models import Dataset as DatasetModel
from ..schemas.dataset import Dataset
from ..services.automl import AzureAutoMLService

router = APIRouter()
service = AzureAutoMLService()


@router.post("/datasets", response_model=Dataset)
async def create_dataset(
    file: UploadFile = File(...),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
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


@router.get("/datasets", response_model=list[Dataset])
async def list_datasets(user=Depends(get_current_user), db: Session = Depends(get_db)):
    records = db.query(DatasetModel).all()
    return [Dataset(**r.__dict__) for r in records]


@router.get("/datasets/{dataset_id}", response_model=Dataset)
async def get_dataset(dataset_id: str, user=Depends(get_current_user), db: Session = Depends(get_db)):
    record = db.get(DatasetModel, dataset_id)
    if not record:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return Dataset(**record.__dict__)


@router.delete("/datasets/{dataset_id}", status_code=204)
async def delete_dataset(dataset_id: str, user=Depends(get_current_user), db: Session = Depends(get_db)):
    record = db.get(DatasetModel, dataset_id)
    if not record:
        raise HTTPException(status_code=404, detail="Dataset not found")
    db.delete(record)
    db.commit()
    return None


@router.put("/datasets/{dataset_id}", response_model=Dataset)
async def update_dataset(
    dataset_id: str,
    dataset: Dataset,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = db.get(DatasetModel, dataset_id)
    if not record:
        raise HTTPException(status_code=404, detail="Dataset not found")
    for field, value in dataset.model_dump().items():
        setattr(record, field, value)
    db.commit()
    db.refresh(record)
    return Dataset(**record.__dict__)
