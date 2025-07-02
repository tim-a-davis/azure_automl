from fastapi import APIRouter, Depends
from ..services.automl import AzureAutoMLService
from ..schemas.model import Model
from ..auth import get_current_user

router = APIRouter()
service = AzureAutoMLService()

@router.get("/models", response_model=list[Model])
async def list_models(user=Depends(get_current_user)):
    return service.list_models()
