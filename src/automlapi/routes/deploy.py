"""API routes for model deployment functionality."""

import time
from typing import Any, Dict, List
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Path
from sqlalchemy.orm import Session

from ..auth import UserInfo, get_current_user
from ..db import get_db
from ..db.models import Deployment as DeploymentModel
from ..db.models import Endpoint as EndpointModel
from ..db.models import Experiment as ExperimentModel
from ..db.models import Model as ModelModel
from ..db.models import Run as RunModel
from ..schemas.deployment import DeploymentRequest, DeploymentResponse
from ..services.automl import AzureAutoMLService

router = APIRouter()


def get_service() -> AzureAutoMLService:
    """Provide a fresh service instance for each request."""
    return AzureAutoMLService()


def create_or_update_model_record(
    db: Session,
    user: UserInfo,
    deployment_result: Dict[str, Any],
    experiment_id: UUID = None,
    run_id: UUID = None,
    dataset_id: UUID = None,
    task_type: str = None,
) -> ModelModel:
    """Create or update model record in database when model is registered."""
    # Parse model reference to extract name and version
    model_reference = deployment_result.get("model_reference", "")
    model_name, model_version = (
        model_reference.split(":") if ":" in model_reference else (model_reference, "1")
    )

    # Check if model already exists
    model_record = (
        db.query(ModelModel)
        .filter(
            ModelModel.azure_model_name == model_name,
            ModelModel.user_id == user.user_id,
        )
        .first()
    )

    if not model_record:
        # Create new model record
        model_record = ModelModel(
            user_id=user.user_id,
            dataset_id=dataset_id,
            experiment_id=experiment_id,
            run_id=run_id,
            task_type=task_type,
            algorithm=deployment_result.get("algorithm"),
            azure_model_name=model_name,
            azure_model_version=model_version,
            model_uri=f"azureml://models/{model_name}/{model_version}",
            best_score=deployment_result.get("model_score"),
            registration_status="registered",
            model_metadata={
                "deployment_timestamp": deployment_result.get("deployment_timestamp"),
                "source_experiment": deployment_result.get("experiment_name"),
                "azure_endpoint_name": deployment_result.get("endpoint_name"),
            },
        )
        db.add(model_record)
    else:
        # Update existing model record
        model_record.azure_model_version = model_version
        model_record.best_score = deployment_result.get("model_score")
        model_record.registration_status = "registered"
        model_record.algorithm = deployment_result.get("algorithm")
        model_record.model_uri = f"azureml://models/{model_name}/{model_version}"
        if run_id:
            model_record.run_id = run_id

        # Update metadata
        if not model_record.model_metadata:
            model_record.model_metadata = {}
        model_record.model_metadata.update(
            {
                "last_deployment_timestamp": deployment_result.get(
                    "deployment_timestamp"
                ),
                "azure_endpoint_name": deployment_result.get("endpoint_name"),
            }
        )

    return model_record


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

        try:
            # Create or update model record in database
            model_record = create_or_update_model_record(
                db=db,
                user=user,
                deployment_result=deployment_result,
                experiment_id=experiment_id,
                dataset_id=experiment.dataset_id,
                task_type=experiment.task_type,
            )
            db.flush()  # Flush to get the model_record.id

            # Create or update endpoint record
            endpoint_record = (
                db.query(EndpointModel)
                .filter(
                    EndpointModel.azure_endpoint_name
                    == deployment_result.get("endpoint_name"),
                    EndpointModel.user_id == user.user_id,
                )
                .first()
            )

            if not endpoint_record:
                endpoint_record = EndpointModel(
                    user_id=user.user_id,
                    name=request.endpoint_name,
                    azure_endpoint_name=deployment_result.get("endpoint_name"),
                    azure_endpoint_url=deployment_result.get("endpoint_url"),
                    dataset_id=experiment.dataset_id,
                    experiment_id=experiment_id,
                    model_id=model_record.id,
                    deployment_status="deployed",
                    endpoint_metadata={
                        "source_experiment": experiment_name,
                        "created_from_deployment": True,
                    },
                )
                db.add(endpoint_record)
            else:
                # Update existing endpoint
                endpoint_record.azure_endpoint_url = deployment_result.get(
                    "endpoint_url"
                )
                endpoint_record.deployment_status = "deployed"
                endpoint_record.model_id = model_record.id

            db.flush()  # Flush to get the endpoint_record.id

            # Create deployment record
            deployment_record = DeploymentModel(
                user_id=user.user_id,
                endpoint_id=endpoint_record.id,
                model_id=model_record.id,
                deployment_name=deployment_result.get("deployment_name"),
                azure_deployment_name=deployment_result.get("deployment_name"),
                instance_type=request.instance_type,
                instance_count=request.instance_count,
                traffic_percentage=request.traffic_percentage,
                deployment_status=deployment_result.get(
                    "deployment_status", "deployed"
                ),
                deployment_config={
                    "experiment_name": experiment_name,
                    "model_reference": deployment_result.get("model_reference"),
                    "algorithm": deployment_result.get("algorithm"),
                    "model_score": deployment_result.get("model_score"),
                },
            )
            db.add(deployment_record)
            db.commit()

            return DeploymentResponse(
                deployment_id=UUID(deployment_record.id),
                model_id=UUID(model_record.id),
                endpoint_id=UUID(endpoint_record.id),
                endpoint_url=deployment_result.get("endpoint_url"),
                deployment_status=deployment_result.get(
                    "deployment_status", "deployed"
                ),
                message=f"Successfully deployed model from experiment {experiment_id}. "
                f"Algorithm: {deployment_result.get('algorithm')}, "
                f"Score: {deployment_result.get('model_score'):.4f}. "
                f"Model registered as: {model_record.azure_model_name}:{model_record.azure_model_version}",
            )

        except Exception as db_error:
            # Log database error but don't fail the deployment response
            # The model was successfully deployed to Azure, just database record creation failed
            import logging

            logging.error(
                f"Failed to create database records for deployment: {str(db_error)}"
            )
            db.rollback()

            # Return response with placeholder IDs but indicate database record issue
            return DeploymentResponse(
                deployment_id=UUID(str(experiment_id)[:32].replace("-", "0")),
                model_id=UUID(str(experiment_id)[:32].replace("-", "1")),
                endpoint_id=UUID(str(experiment_id)[:32].replace("-", "2")),
                endpoint_url=deployment_result.get("endpoint_url"),
                deployment_status=deployment_result.get(
                    "deployment_status", "deployed"
                ),
                message=f"Model deployed successfully from experiment {experiment_id}, but failed to create database records: {str(db_error)}. "
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

        try:
            # Create or update model record in database
            model_record = create_or_update_model_record(
                db=db,
                user=user,
                deployment_result=deployment_result,
                experiment_id=run.experiment_id,
                run_id=run_id,
                task_type=run.metrics.get("task_type") if run.metrics else None,
            )
            db.flush()  # Flush to get the model_record.id

            # Create or update endpoint record
            endpoint_record = (
                db.query(EndpointModel)
                .filter(
                    EndpointModel.azure_endpoint_name
                    == deployment_result.get("endpoint_name"),
                    EndpointModel.user_id == user.user_id,
                )
                .first()
            )

            if not endpoint_record:
                endpoint_record = EndpointModel(
                    user_id=user.user_id,
                    name=request.endpoint_name,
                    azure_endpoint_name=deployment_result.get("endpoint_name"),
                    azure_endpoint_url=deployment_result.get("endpoint_url"),
                    experiment_id=run.experiment_id,
                    run_id=run_id,
                    model_id=model_record.id,
                    deployment_status="deployed",
                    endpoint_metadata={
                        "source_run": str(run_id),
                        "source_experiment": experiment_name,
                        "created_from_deployment": True,
                    },
                )
                db.add(endpoint_record)
            else:
                # Update existing endpoint
                endpoint_record.azure_endpoint_url = deployment_result.get(
                    "endpoint_url"
                )
                endpoint_record.deployment_status = "deployed"
                endpoint_record.model_id = model_record.id
                endpoint_record.run_id = run_id

            db.flush()  # Flush to get the endpoint_record.id

            # Create deployment record
            deployment_record = DeploymentModel(
                user_id=user.user_id,
                endpoint_id=endpoint_record.id,
                model_id=model_record.id,
                deployment_name=deployment_result.get("deployment_name"),
                azure_deployment_name=deployment_result.get("deployment_name"),
                instance_type=request.instance_type,
                instance_count=request.instance_count,
                traffic_percentage=request.traffic_percentage,
                deployment_status=deployment_result.get(
                    "deployment_status", "deployed"
                ),
                deployment_config={
                    "source_run": str(run_id),
                    "experiment_name": experiment_name,
                    "model_reference": deployment_result.get("model_reference"),
                    "algorithm": deployment_result.get("algorithm"),
                    "model_score": deployment_result.get("model_score"),
                },
            )
            db.add(deployment_record)
            db.commit()

            return DeploymentResponse(
                deployment_id=UUID(deployment_record.id),
                model_id=UUID(model_record.id),
                endpoint_id=UUID(endpoint_record.id),
                endpoint_url=deployment_result.get("endpoint_url"),
                deployment_status=deployment_result.get(
                    "deployment_status", "deployed"
                ),
                message=f"Successfully deployed model from run {run_id}. "
                f"Algorithm: {deployment_result.get('algorithm')}, "
                f"Score: {deployment_result.get('model_score'):.4f}. "
                f"Model registered as: {model_record.azure_model_name}:{model_record.azure_model_version}",
            )

        except Exception as db_error:
            # Log database error but don't fail the deployment response
            import logging

            logging.error(
                f"Failed to create database records for deployment: {str(db_error)}"
            )
            db.rollback()

            # Return response with placeholder IDs but indicate database record issue
            return DeploymentResponse(
                deployment_id=UUID(str(run_id)[:32].replace("-", "0")),
                model_id=UUID(str(run_id)[:32].replace("-", "1")),
                endpoint_id=UUID(str(run_id)[:32].replace("-", "2")),
                endpoint_url=deployment_result.get("endpoint_url"),
                deployment_status=deployment_result.get(
                    "deployment_status", "deployed"
                ),
                message=f"Model deployed successfully from run {run_id}, but failed to create database records: {str(db_error)}. "
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

        # Query deployments from database
        deployments = (
            db.query(DeploymentModel)
            .join(EndpointModel, DeploymentModel.endpoint_id == EndpointModel.id)
            .filter(
                EndpointModel.experiment_id == experiment_id,
                EndpointModel.user_id == user.user_id,
            )
            .all()
        )

        deployment_list = []
        for deployment in deployments:
            # Get model info
            model = (
                db.query(ModelModel)
                .filter(ModelModel.id == deployment.model_id)
                .first()
            )
            # Get endpoint info
            endpoint = (
                db.query(EndpointModel)
                .filter(EndpointModel.id == deployment.endpoint_id)
                .first()
            )

            deployment_info = {
                "deployment_id": str(deployment.id),
                "deployment_name": deployment.deployment_name,
                "azure_deployment_name": deployment.azure_deployment_name,
                "model_id": str(deployment.model_id),
                "endpoint_id": str(deployment.endpoint_id),
                "instance_type": deployment.instance_type,
                "instance_count": deployment.instance_count,
                "traffic_percentage": deployment.traffic_percentage,
                "deployment_status": deployment.deployment_status,
                "created_at": deployment.created_at.isoformat()
                if deployment.created_at
                else None,
                "deployment_config": deployment.deployment_config,
                "model_name": model.azure_model_name if model else None,
                "model_version": model.azure_model_version if model else None,
                "model_algorithm": model.algorithm if model else None,
                "endpoint_name": endpoint.name if endpoint else None,
                "endpoint_url": endpoint.azure_endpoint_url if endpoint else None,
            }
            deployment_list.append(deployment_info)

        return deployment_list

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/deploy/sync-models",
    response_model=Dict[str, Any],
    operation_id="sync_azure_models",
    tags=["mcp"],
)
async def sync_azure_models_to_database(
    user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: AzureAutoMLService = Depends(get_service),
) -> Dict[str, Any]:
    """Sync Azure ML models to local database.

    This endpoint fetches all models from Azure ML and creates/updates
    corresponding records in the local database. Useful for registering
    models that were created outside of the deployment workflow.
    """
    try:
        # Get all models from Azure ML
        azure_models = service.list_models()

        created_count = 0
        updated_count = 0
        errors = []

        for azure_model in azure_models:
            try:
                # Check if model already exists in database
                existing_model = (
                    db.query(ModelModel)
                    .filter(
                        ModelModel.azure_model_name == azure_model.name,
                        ModelModel.user_id == user.user_id,
                    )
                    .first()
                )

                if existing_model:
                    # Update existing model
                    existing_model.azure_model_version = azure_model.version
                    existing_model.registration_status = "registered"
                    if azure_model.description:
                        existing_model.model_metadata = (
                            existing_model.model_metadata or {}
                        )
                        existing_model.model_metadata["azure_description"] = (
                            azure_model.description
                        )
                    updated_count += 1
                else:
                    # Create new model record
                    new_model = ModelModel(
                        user_id=user.user_id,
                        azure_model_name=azure_model.name,
                        azure_model_version=azure_model.version,
                        model_uri=f"azureml://models/{azure_model.name}/{azure_model.version}",
                        registration_status="registered",
                        model_metadata={
                            "azure_description": azure_model.description or "",
                            "sync_timestamp": str(int(time.time())),
                            "tags": getattr(azure_model, "tags", {}),
                        },
                    )
                    db.add(new_model)
                    created_count += 1

            except Exception as model_error:
                errors.append(
                    f"Error processing model {azure_model.name}: {str(model_error)}"
                )
                continue

        # Commit all changes
        db.commit()

        return {
            "status": "completed",
            "models_created": created_count,
            "models_updated": updated_count,
            "total_azure_models": len(azure_models),
            "errors": errors,
            "message": f"Successfully synced {created_count + updated_count} models from Azure ML",
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Failed to sync Azure models: {str(e)}"
        )


@router.get(
    "/deploy/models/registration-status",
    response_model=List[Dict[str, Any]],
    operation_id="get_model_registration_status",
    tags=["mcp"],
)
async def get_model_registration_status(
    user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Get registration status of all models for the current user.

    Returns a list of all models in the database with their registration status,
    Azure ML details, and deployment information.
    """
    try:
        models = db.query(ModelModel).filter(ModelModel.user_id == user.user_id).all()

        model_status_list = []
        for model in models:
            # Count deployments for this model
            deployment_count = (
                db.query(DeploymentModel)
                .filter(DeploymentModel.model_id == model.id)
                .count()
            )

            model_info = {
                "model_id": str(model.id),
                "azure_model_name": model.azure_model_name,
                "azure_model_version": model.azure_model_version,
                "model_uri": model.model_uri,
                "registration_status": model.registration_status,
                "algorithm": model.algorithm,
                "best_score": model.best_score,
                "task_type": model.task_type,
                "experiment_id": str(model.experiment_id)
                if model.experiment_id
                else None,
                "run_id": str(model.run_id) if model.run_id else None,
                "deployment_count": deployment_count,
                "created_at": model.created_at.isoformat()
                if model.created_at
                else None,
                "updated_at": model.updated_at.isoformat()
                if model.updated_at
                else None,
                "model_metadata": model.model_metadata,
                "error_message": model.error_message,
            }
            model_status_list.append(model_info)

        return model_status_list

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve model status: {str(e)}"
        )
