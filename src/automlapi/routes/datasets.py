"""API routes for managing datasets."""

import json

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Path,
    Query,
    Response,
    UploadFile,
)
from sqlalchemy.orm import Session

from ..auth import UserInfo, get_current_user, require_maintainer
from ..db import get_db
from ..db.models import Dataset as DatasetModel
from ..db.models import Model as ModelModel
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
    name: str = Form(..., description="Name for the dataset"),
    description: str = Form(None, description="Optional description for the dataset"),
    tags: str = Form(
        None, description="Optional JSON string of tags for categorization"
    ),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
    service: AzureAutoMLService = Depends(get_service),
) -> Dataset:
    """Upload a dataset file.

    Reads the provided file and stores it in the workspace. Returns metadata
    about the created dataset record.
    """

    # Parse tags if provided
    parsed_tags = None
    if tags:
        try:
            parsed_tags = json.loads(tags)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON format for tags")

    # Upload dataset to Azure ML
    data = await file.read()
    try:
        dataset_info = service.upload_dataset(name, data)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    # Create database record
    record = DatasetModel(
        id=dataset_info["id"],
        uploaded_by=user.user_id,
        asset_id=dataset_info.get("asset_id"),
        name=dataset_info["name"],
        version=dataset_info.get("version"),
        storage_uri=dataset_info.get("storage_uri"),
        tags=parsed_tags,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    # Convert the database record to the response schema
    return model_to_schema(record, Dataset)


@router.get(
    "/datasets",
    response_model=list[Dataset],
    operation_id="list_datasets",
    tags=["mcp"],
)
async def list_datasets(
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
    uploaded_by: str = Query(None, description="Filter datasets by uploader user ID"),
) -> list[Dataset]:
    """List uploaded datasets.

    Returns all dataset records stored in the database. Optionally filter by uploader.
    """
    query = db.query(DatasetModel)
    if uploaded_by:
        query = query.filter(DatasetModel.uploaded_by == uploaded_by)

    records = query.all()
    return models_to_schema(records, Dataset)


@router.get(
    "/datasets/{dataset_id}",
    response_model=Dataset,
    operation_id="get_dataset",
    tags=["mcp"],
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
@require_maintainer
async def delete_dataset(
    dataset_id: str = Path(..., description="Dataset identifier"),
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Remove an existing dataset.

    Deletes the dataset record and associated storage if found.
    Only MAINTAINERs and ADMINs can delete datasets.
    """
    record = db.get(DatasetModel, dataset_id)
    if not record:
        raise HTTPException(status_code=404, detail="Dataset not found")
    db.delete(record)
    db.commit()
    return Response(status_code=204)


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


@router.get(
    "/datasets/search",
    response_model=list[Dataset],
    operation_id="search_datasets",
    tags=["mcp"],
)
async def search_datasets(
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
    tag_key: str = Query(None, description="Search by tag key"),
    tag_value: str = Query(None, description="Search by tag value"),
    name_like: str = Query(None, description="Search by dataset name (partial match)"),
) -> list[Dataset]:
    """Search datasets by tags or name.

    Allows filtering datasets by tag key/value pairs or partial name matching.
    """
    query = db.query(DatasetModel)

    if tag_key and tag_value:
        # Search for datasets where tags contain the key-value pair
        query = query.filter(DatasetModel.tags.op("->>").text(tag_key) == tag_value)
    elif tag_key:
        # Search for datasets that have the tag key (regardless of value)
        query = query.filter(DatasetModel.tags.op("?").text(tag_key))

    if name_like:
        query = query.filter(DatasetModel.name.ilike(f"%{name_like}%"))

    records = query.all()
    return models_to_schema(records, Dataset)


@router.get(
    "/datasets/{dataset_id}/experiments",
    response_model=list,
    operation_id="get_dataset_experiments",
)
async def get_dataset_experiments(
    dataset_id: str = Path(..., description="Dataset identifier"),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get experiments that used this dataset.

    Returns a list of experiments that were run using the specified dataset.
    """
    from ..db.models import Experiment as ExperimentModel

    # First check if dataset exists
    dataset = db.get(DatasetModel, dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Get experiments that used this dataset
    experiments = (
        db.query(ExperimentModel).filter(ExperimentModel.dataset_id == dataset_id).all()
    )

    return [
        {"id": exp.id, "task_type": exp.task_type, "created_at": exp.created_at}
        for exp in experiments
    ]


@router.get(
    "/datasets/{dataset_id}/models",
    response_model=list,
    operation_id="get_dataset_models",
)
async def get_dataset_models(
    dataset_id: str = Path(..., description="Dataset identifier"),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get models trained on this dataset.

    Returns a list of models that were trained using the specified dataset.
    """

    # First check if dataset exists
    dataset = db.get(DatasetModel, dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Get models that used this dataset
    models = db.query(ModelModel).filter(ModelModel.dataset_id == dataset_id).all()

    return [
        {
            "id": model.id,
            "task_type": model.task_type,
            "azure_model_id": model.azure_model_id,
            "created_at": model.created_at,
        }
        for model in models
    ]
