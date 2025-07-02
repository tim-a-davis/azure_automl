from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..db import get_db
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
    dataset = service.upload_dataset(file.filename, data)
    return dataset


@router.get("/datasets", response_model=list[Dataset])
async def list_datasets(user=Depends(get_current_user), db: Session = Depends(get_db)):
    return service.list_datasets()
    return service.list_datasets()
