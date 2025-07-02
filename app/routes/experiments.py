from fastapi import APIRouter, Depends
from ..services.automl import AzureAutoMLService
from ..schemas.experiment import Experiment
from ..schemas.run import Run
from ..auth import get_current_user

router = APIRouter()
service = AzureAutoMLService()

@router.post("/experiments", response_model=Run)
async def start_experiment(exp: Experiment, user=Depends(get_current_user)):
    return service.start_experiment(exp)

@router.get("/experiments", response_model=list[Experiment])
async def list_experiments(user=Depends(get_current_user)):
    return service.list_experiments()
