"""API routes for model deployment functionality."""

from typing import Any, Dict, List
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Path
from sqlalchemy.orm import Session

from ..auth import UserInfo, get_current_user
from ..db import get_db
from ..db.models import Experiment as ExperimentModel
from ..db.models import Run as RunModel
from ..schemas.deployment import DeploymentRequest, DeploymentResponse
from ..services.automl import AzureAutoMLService

router = APIRouter()


def get_service() -> AzureAutoMLService:
    """Provide a fresh service instance for each request."""
    return AzureAutoMLService()


@router.post(
    "/deploy/experiment/{experiment_id}",
    response_model=DeploymentResponse,
    operation_id="deploy_experiment",
    tags=["mcp"],
)
async def deploy_best_model_from_experiment(
    experiment_id: UUID = Path(description="Experiment ID to deploy from"),
    request: DeploymentRequest = None,
    user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: AzureAutoMLService = Depends(get_service),
) -> DeploymentResponse:
    """Deploy the best model from a completed AutoML experiment.

    Finds the highest-scoring model from the experiment, registers it,
    and deploys it to a new or existing endpoint.
    """
    try:
        # Verify experiment exists and belongs to user
        experiment = (
            db.query(ExperimentModel)
            .filter(
                ExperimentModel.id == experiment_id,
                ExperimentModel.user_id == user.user_id,
            )
            .first()
        )

        if not experiment:
            raise HTTPException(
                status_code=404,
                detail=f"Experiment {experiment_id} not found or access denied",
            )

        # Use experiment ID as the experiment name for Azure ML
        experiment_name = str(experiment_id)

        # Deploy using the service
        deployment_result = service.deploy_best_model_from_experiment(
            experiment_name=experiment_name,
            endpoint_name=request.endpoint_name,
            deployment_name=request.deployment_name,
            instance_type=request.instance_type,
            instance_count=request.instance_count,
            traffic_percentage=request.traffic_percentage,
        )

        # TODO: Store deployment record in database
        # This would create records in the Deployment and Endpoint tables
        # For now, return the service response

        return DeploymentResponse(
            deployment_id=UUID(
                deployment_result["best_job_name"][:32].replace("-", "0")
            ),  # Placeholder
            model_id=UUID(str(experiment_id)[:32].replace("-", "0")),  # Placeholder
            endpoint_id=UUID(str(experiment_id)[:32].replace("-", "1")),  # Placeholder
            endpoint_url=deployment_result.get("endpoint_url"),
            deployment_status=deployment_result.get("deployment_status", "deployed"),
            message=f"Successfully deployed model from experiment {experiment_id}. "
            f"Algorithm: {deployment_result.get('algorithm')}, "
            f"Score: {deployment_result.get('model_score'):.4f}",
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/deploy/run/{run_id}",
    response_model=DeploymentResponse,
    operation_id="deploy_run",
    tags=["mcp"],
)
async def deploy_model_from_run(
    run_id: UUID = Path(description="Run ID to deploy from"),
    request: DeploymentRequest = None,
    user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: AzureAutoMLService = Depends(get_service),
) -> DeploymentResponse:
    """Deploy a model from a specific AutoML run.

    Registers the model from the specified run and deploys it to an endpoint.
    """
    try:
        # Verify run exists and belongs to user
        run = (
            db.query(RunModel)
            .filter(RunModel.id == run_id, RunModel.user_id == user.user_id)
            .first()
        )

        if not run:
            raise HTTPException(
                status_code=404, detail=f"Run {run_id} not found or access denied"
            )

        # For run-specific deployment, we would need to implement
        # deploy_best_model_from_run method in the service
        # For now, use experiment deployment as fallback
        experiment_name = str(run.experiment_id) if run.experiment_id else str(run_id)

        deployment_result = service.deploy_best_model_from_experiment(
            experiment_name=experiment_name,
            endpoint_name=request.endpoint_name,
            deployment_name=request.deployment_name,
            instance_type=request.instance_type,
            instance_count=request.instance_count,
            traffic_percentage=request.traffic_percentage,
        )

        return DeploymentResponse(
            deployment_id=UUID(str(run_id)[:32].replace("-", "0")),  # Placeholder
            model_id=UUID(str(run_id)[:32].replace("-", "1")),  # Placeholder
            endpoint_id=UUID(str(run_id)[:32].replace("-", "2")),  # Placeholder
            endpoint_url=deployment_result.get("endpoint_url"),
            deployment_status=deployment_result.get("deployment_status", "deployed"),
            message=f"Successfully deployed model from run {run_id}. "
            f"Algorithm: {deployment_result.get('algorithm')}, "
            f"Score: {deployment_result.get('model_score'):.4f}",
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/deploy/status/{endpoint_name}/{deployment_name}",
    response_model=Dict[str, Any],
    operation_id="get_deployment_status",
    tags=["mcp"],
)
async def get_deployment_status(
    endpoint_name: str = Path(description="Endpoint name"),
    deployment_name: str = Path(description="Deployment name"),
    user: UserInfo = Depends(get_current_user),
    service: AzureAutoMLService = Depends(get_service),
) -> Dict[str, Any]:
    """Get the status and details of a specific deployment."""
    try:
        status = service.get_deployment_status(endpoint_name, deployment_name)
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/deploy/metrics/{endpoint_name}/{deployment_name}",
    response_model=Dict[str, Any],
    operation_id="get_deployment_metrics",
    tags=["mcp"],
)
async def get_deployment_metrics(
    endpoint_name: str = Path(description="Endpoint name"),
    deployment_name: str = Path(description="Deployment name"),
    user: UserInfo = Depends(get_current_user),
    service: AzureAutoMLService = Depends(get_service),
) -> Dict[str, Any]:
    """Get performance metrics for a deployment."""
    try:
        metrics = service.get_deployment_metrics(endpoint_name, deployment_name)
        return metrics
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/deploy/{endpoint_name}/traffic",
    response_model=Dict[str, Any],
    operation_id="update_deployment_traffic",
    tags=["mcp"],
)
async def update_deployment_traffic(
    endpoint_name: str = Path(description="Endpoint name"),
    *,
    traffic_allocation: Dict[str, int] = Body(
        description="Traffic allocation mapping deployment names to percentages"
    ),
    user: UserInfo = Depends(get_current_user),
    service: AzureAutoMLService = Depends(get_service),
) -> Dict[str, Any]:
    """Update traffic allocation for deployments on an endpoint.

    The traffic_allocation should be a dict mapping deployment names to
    traffic percentages (must sum to 100).
    """
    try:
        # Validate traffic allocation
        total_traffic = sum(traffic_allocation.values())
        if total_traffic != 100:
            raise HTTPException(
                status_code=400,
                detail=f"Traffic allocation must sum to 100, got {total_traffic}",
            )

        updated_traffic = service.update_endpoint_traffic(
            endpoint_name, traffic_allocation
        )
        return {
            "endpoint_name": endpoint_name,
            "traffic_allocation": updated_traffic,
            "message": "Traffic allocation updated successfully",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/deploy/{endpoint_name}/{deployment_name}",
    response_model=Dict[str, str],
    operation_id="delete_deployment",
    tags=["mcp"],
)
async def delete_deployment(
    endpoint_name: str = Path(description="Endpoint name"),
    deployment_name: str = Path(description="Deployment name"),
    user: UserInfo = Depends(get_current_user),
    service: AzureAutoMLService = Depends(get_service),
) -> Dict[str, str]:
    """Delete a deployment from an endpoint.

    Note: This will remove the deployment from Azure ML. Use with caution.
    """
    try:
        # For now, we don't have a delete_deployment method in the service
        # This would need to be implemented
        raise HTTPException(
            status_code=501, detail="Deployment deletion not yet implemented"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/deploy/experiments/{experiment_id}/deployments",
    response_model=List[Dict[str, Any]],
    operation_id="list_experiment_deployments",
    tags=["mcp"],
)
async def list_experiment_deployments(
    experiment_id: UUID = Path(description="Experiment ID"),
    user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """List all deployments created from an experiment."""
    try:
        # Verify experiment exists and belongs to user
        experiment = (
            db.query(ExperimentModel)
            .filter(
                ExperimentModel.id == experiment_id,
                ExperimentModel.user_id == user.user_id,
            )
            .first()
        )

        if not experiment:
            raise HTTPException(
                status_code=404,
                detail=f"Experiment {experiment_id} not found or access denied",
            )

        # TODO: Query deployments from database
        # For now, return empty list
        return []

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
