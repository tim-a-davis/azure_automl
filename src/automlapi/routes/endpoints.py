"""API routes for managing deployment endpoints."""

import json
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Path, Response, WebSocket
from sqlalchemy.orm import Session

from ..auth import UserInfo, get_current_user, require_maintainer
from ..db import get_db
from ..db.models import Endpoint as EndpointModel
from ..schemas.endpoint import Endpoint
from ..services.automl import AzureAutoMLService
from ..utils import model_to_schema, models_to_schema

router = APIRouter()


def get_service() -> AzureAutoMLService:
    """Provide a fresh service instance for each request."""
    return AzureAutoMLService()


@router.post(
    "/endpoints",
    response_model=Endpoint,
    operation_id="create_endpoint",
    tags=["mcp"],
)
async def create_endpoint(
    endpoint_name: str,
    description: Optional[str] = None,
    tags: Optional[str] = None,
    user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: AzureAutoMLService = Depends(get_service),
) -> Endpoint:
    """Create a deployment endpoint.

    Creates an actual Azure ML online endpoint and stores the metadata in the database.
    """
    # Parse tags if provided
    parsed_tags = None
    if tags:
        try:
            parsed_tags = json.loads(tags)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON format for tags")

    try:
        # Create the endpoint in Azure ML
        azure_endpoint = service.create_endpoint(
            endpoint_name=endpoint_name, description=description, tags=parsed_tags
        )

        # Store the endpoint metadata in our database
        record = EndpointModel(
            id=azure_endpoint.id,
            user_id=user.user_id,  # Store the user ID who created the endpoint
            name=azure_endpoint.name,
            azure_endpoint_name=azure_endpoint.azure_endpoint_name,
            azure_endpoint_url=azure_endpoint.azure_endpoint_url,
            auth_mode=azure_endpoint.auth_mode,
            provisioning_state=azure_endpoint.provisioning_state,
            description=azure_endpoint.description,
            deployments=azure_endpoint.deployments,
            traffic=azure_endpoint.traffic,
            tags=azure_endpoint.tags,
        )
        db.add(record)
        db.commit()
        db.refresh(record)

        return model_to_schema(record, Endpoint)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to create endpoint: {str(e)}"
        )


@router.get(
    "/endpoints",
    response_model=list[Endpoint],
    operation_id="list_endpoints",
    tags=["mcp"],
)
async def list_endpoints(
    user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: AzureAutoMLService = Depends(get_service),
) -> list[Endpoint]:
    """List deployment endpoints.

    Returns all endpoint records from both Azure ML and the local database.
    """
    try:
        # Get endpoints from Azure ML
        azure_endpoints = service.list_endpoints()

        # Get endpoints from local database
        db_records = db.query(EndpointModel).all()
        db_endpoint_names = {
            record.azure_endpoint_name
            for record in db_records
            if record.azure_endpoint_name
        }

        # Sync any new endpoints from Azure ML to our database
        for azure_endpoint in azure_endpoints:
            if (
                hasattr(azure_endpoint, "name")
                and azure_endpoint.name not in db_endpoint_names
            ):
                # This endpoint exists in Azure ML but not in our database, so add it
                record = EndpointModel(
                    user_id=user.user_id,
                    name=azure_endpoint.name,
                    azure_endpoint_name=azure_endpoint.name,
                    azure_endpoint_url=getattr(
                        azure_endpoint, "azure_endpoint_url", None
                    ),
                    auth_mode=getattr(azure_endpoint, "auth_mode", "key"),
                    provisioning_state=getattr(
                        azure_endpoint, "provisioning_state", None
                    ),
                    description=getattr(azure_endpoint, "description", None),
                    deployments=getattr(azure_endpoint, "deployments", None),
                    traffic=getattr(azure_endpoint, "traffic", None),
                    tags=getattr(azure_endpoint, "tags", None),
                )
                db.add(record)

        db.commit()

        # Return updated list from database
        updated_records = db.query(EndpointModel).all()
        return models_to_schema(updated_records, Endpoint)
    except Exception:
        # If Azure ML call fails, fall back to database records
        records = db.query(EndpointModel).all()
        return models_to_schema(records, Endpoint)


@router.get(
    "/endpoints/{endpoint_id}",
    response_model=Endpoint,
    operation_id="get_endpoint",
    tags=["mcp"],
)
async def get_endpoint(
    endpoint_id: str = Path(..., description="Endpoint identifier"),
    user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: AzureAutoMLService = Depends(get_service),
) -> Endpoint:
    """Fetch an endpoint by ID.

    Returns the stored endpoint record if present, with updated information from Azure ML.
    """
    # First try to get from database
    record = db.get(EndpointModel, endpoint_id)
    if not record:
        raise HTTPException(status_code=404, detail="Endpoint not found")

    # If we have the Azure endpoint name, try to get fresh data from Azure ML
    if record.azure_endpoint_name:
        try:
            azure_endpoint = service.get_endpoint(record.azure_endpoint_name)

            # Update database record with fresh Azure ML data
            record.azure_endpoint_url = azure_endpoint.azure_endpoint_url
            record.provisioning_state = azure_endpoint.provisioning_state
            record.deployments = azure_endpoint.deployments
            record.traffic = azure_endpoint.traffic
            record.tags = azure_endpoint.tags

            db.commit()
            db.refresh(record)
        except Exception:
            # If Azure ML call fails, continue with database data
            pass

    return model_to_schema(record, Endpoint)


@router.delete(
    "/endpoints/{endpoint_id}",
    status_code=204,
    operation_id="delete_endpoint",
)
@require_maintainer
async def delete_endpoint(
    endpoint_id: str = Path(..., description="Endpoint identifier"),
    current_user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: AzureAutoMLService = Depends(get_service),
):
    """Remove a deployment endpoint.

    Deletes the endpoint from both Azure ML and the database.
    Only MAINTAINERs and ADMINs can delete endpoints.
    """
    record = db.get(EndpointModel, endpoint_id)
    if not record:
        raise HTTPException(status_code=404, detail="Endpoint not found")

    # Delete from Azure ML if we have the Azure endpoint name
    if record.azure_endpoint_name:
        try:
            service.delete_endpoint(record.azure_endpoint_name)
        except Exception as e:
            # If Azure ML deletion fails, we'll still remove from database
            # but return an error message
            raise HTTPException(
                status_code=500, detail=f"Failed to delete from Azure ML: {str(e)}"
            )

    # Delete from database
    db.delete(record)
    db.commit()
    return Response(status_code=204)


@router.put(
    "/endpoints/{endpoint_id}",
    response_model=Endpoint,
    operation_id="update_endpoint",
    tags=["mcp"],
)
async def update_endpoint(
    endpoint_id: str = Path(..., description="Endpoint identifier"),
    description: Optional[str] = None,
    tags: Optional[str] = None,
    user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: AzureAutoMLService = Depends(get_service),
) -> Endpoint:
    """Update an endpoint record.

    Updates the endpoint in both Azure ML and the database.
    """
    record = db.get(EndpointModel, endpoint_id)
    if not record:
        raise HTTPException(status_code=404, detail="Endpoint not found")

    # Parse tags if provided
    parsed_tags = None
    if tags:
        try:
            parsed_tags = json.loads(tags)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON format for tags")

    # Update in Azure ML if we have the Azure endpoint name
    if record.azure_endpoint_name:
        try:
            azure_endpoint = service.update_endpoint(
                endpoint_name=record.azure_endpoint_name,
                description=description,
                tags=parsed_tags,
            )

            # Update database record with Azure ML response
            if description is not None:
                record.description = azure_endpoint.description
            if parsed_tags is not None:
                record.tags = azure_endpoint.tags
            record.provisioning_state = azure_endpoint.provisioning_state
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to update in Azure ML: {str(e)}"
            )
    else:
        # Update local record only
        if description is not None:
            record.description = description
        if parsed_tags is not None:
            record.tags = parsed_tags

    db.commit()
    db.refresh(record)
    return model_to_schema(record, Endpoint)


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


@router.post(
    "/endpoints/{endpoint_id}/deployments",
    operation_id="create_deployment",
    tags=["mcp"],
)
async def create_deployment(
    endpoint_id: str = Path(..., description="Endpoint identifier"),
    deployment_name: str = Form(..., description="Name for the deployment"),
    model_name: str = Form(..., description="Model name to deploy"),
    model_version: Optional[str] = Form(
        None, description="Model version (latest if not specified)"
    ),
    instance_type: str = Form("Standard_DS3_v2", description="Azure instance type"),
    instance_count: int = Form(1, description="Number of instances"),
    traffic_percentage: int = Form(
        0, description="Traffic percentage for this deployment"
    ),
    user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: AzureAutoMLService = Depends(get_service),
):
    """Create a deployment for an endpoint.

    Creates a new deployment for the specified endpoint with the given model.
    """
    record = db.get(EndpointModel, endpoint_id)
    if not record:
        raise HTTPException(status_code=404, detail="Endpoint not found")

    if not record.azure_endpoint_name:
        raise HTTPException(
            status_code=400, detail="Endpoint is not linked to Azure ML"
        )

    try:
        deployment = service.create_deployment(
            endpoint_name=record.azure_endpoint_name,
            deployment_name=deployment_name,
            model_name=model_name,
            model_version=model_version,
            instance_type=instance_type,
            instance_count=instance_count,
            traffic_percentage=traffic_percentage,
        )

        # Update the endpoint record with the new deployment info
        if not record.deployments:
            record.deployments = {}
        record.deployments[deployment_name] = deployment

        db.commit()
        db.refresh(record)

        return {"message": "Deployment created successfully", "deployment": deployment}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to create deployment: {str(e)}"
        )


@router.get(
    "/endpoints/{endpoint_id}/deployments",
    operation_id="list_deployments",
    tags=["mcp"],
)
async def list_deployments(
    endpoint_id: str = Path(..., description="Endpoint identifier"),
    user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: AzureAutoMLService = Depends(get_service),
):
    """List all deployments for an endpoint."""
    record = db.get(EndpointModel, endpoint_id)
    if not record:
        raise HTTPException(status_code=404, detail="Endpoint not found")

    if not record.azure_endpoint_name:
        raise HTTPException(
            status_code=400, detail="Endpoint is not linked to Azure ML"
        )

    try:
        deployments = service.list_endpoint_deployments(record.azure_endpoint_name)
        return {"deployments": deployments}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to list deployments: {str(e)}"
        )


@router.put(
    "/endpoints/{endpoint_id}/traffic",
    operation_id="update_traffic",
    tags=["mcp"],
)
async def update_traffic(
    endpoint_id: str = Path(..., description="Endpoint identifier"),
    traffic_allocation: str = Form(
        ..., description="JSON string of traffic allocation"
    ),
    user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: AzureAutoMLService = Depends(get_service),
):
    """Update traffic allocation for an endpoint."""
    record = db.get(EndpointModel, endpoint_id)
    if not record:
        raise HTTPException(status_code=404, detail="Endpoint not found")

    if not record.azure_endpoint_name:
        raise HTTPException(
            status_code=400, detail="Endpoint is not linked to Azure ML"
        )

    # Parse traffic allocation
    try:
        parsed_traffic = json.loads(traffic_allocation)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=400, detail="Invalid JSON format for traffic allocation"
        )

    try:
        updated_traffic = service.update_endpoint_traffic(
            record.azure_endpoint_name, parsed_traffic
        )

        # Update the database record
        record.traffic = updated_traffic
        db.commit()
        db.refresh(record)

        return {
            "message": "Traffic allocation updated successfully",
            "traffic": updated_traffic,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to update traffic: {str(e)}"
        )
