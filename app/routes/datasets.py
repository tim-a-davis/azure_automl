from fastapi import APIRouter, UploadFile, File, Depends
from ..services.automl import AzureAutoMLService
from ..schemas.dataset import Dataset
from ..auth import get_current_user

router = APIRouter()
service = AzureAutoMLService()

@router.post("/datasets", response_model=Dataset)
async def create_dataset(file: UploadFile = File(...), user=Depends(get_current_user)):
    data = await file.read()
    return service.upload_dataset(file.filename, data)

@router.get("/datasets", response_model=list[Dataset])
async def list_datasets(user=Depends(get_current_user)):
    return service.list_datasets()
