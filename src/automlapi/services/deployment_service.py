"""Deployment orchestration service combining models and endpoints."""

import logging
from typing import Any, Dict, Optional

from azure.ai.ml.entities import ManagedOnlineDeployment

from .azure_client import AzureMLClientError
from .endpoint_service import EndpointService
from .experiment_service import ExperimentService
from .model_service import ModelService

logger = logging.getLogger(__name__)


class DeploymentService:
    """Service for orchestrating model deployments."""

    def __init__(self):
        self.model_service = ModelService()
        self.endpoint_service = EndpointService()
        self.experiment_service = ExperimentService()

    def deploy_best_model_from_experiment(
        self,
        experiment_name: str,
        endpoint_name: str,
        deployment_name: Optional[str] = None,
        instance_type: str = "Standard_DS3_v2",
        instance_count: int = 1,
        traffic_percentage: int = 100,
    ) -> Dict[str, Any]:
        """Deploy the best model from a completed AutoML experiment."""
        logger.info(f"Deploying best model from experiment: {experiment_name}")

        try:
            # Extract parent job metadata
            parent_metadata = self.experiment_service.extract_parent_job_metadata(
                experiment_name
            )

            # Get child jobs with scores
            jobs_with_scores = self.experiment_service.get_child_jobs_with_scores(
                experiment_name
            )

            if not jobs_with_scores:
                raise AzureMLClientError(
                    f"No jobs with scores found for experiment {experiment_name}"
                )

            # Get the best job and extract its metadata
            best_job = jobs_with_scores[0]
            best_model_metadata = self.model_service.extract_best_model_metadata(
                best_job["name"], best_job
            )

            logger.info(
                f"Best model found: {best_job['name']} with score {best_job['score']:.4f}"
            )

            # Register the model with comprehensive metadata
            model_name = f"automl-best-{experiment_name.replace('_', '-')}"
            model_reference = self.model_service.register_model_from_job(
                best_job["name"], model_name, parent_metadata, best_model_metadata
            )

            # Create or get endpoint with metadata
            endpoint_metadata = {
                "source_experiment": experiment_name,
                "model_algorithm": best_model_metadata.get("algorithm"),
                "model_score": str(best_model_metadata.get("best_score", "")),
            }
            actual_endpoint_name = (
                self.endpoint_service.create_or_get_endpoint_with_metadata(
                    endpoint_name, endpoint_metadata
                )
            )

            # Generate deployment name if not provided
            if deployment_name is None:
                deployment_name = f"deployment-{self.model_service.generate_uuid()[:8]}"

            # Deploy the model
            deployment_result = self.deploy_registered_model(
                model_reference,
                actual_endpoint_name,
                deployment_name,
                instance_type,
                instance_count,
                traffic_percentage,
            )

            # Get endpoint URL
            endpoint = self.endpoint_service.client.online_endpoints.get(
                actual_endpoint_name
            )
            endpoint_url = self.endpoint_service.safe_getattr(
                endpoint, "scoring_uri", "Not available"
            )

            return {
                "experiment_name": experiment_name,
                "best_job_name": best_job["name"],
                "model_reference": model_reference,
                "endpoint_name": actual_endpoint_name,
                "deployment_name": deployment_name,
                "endpoint_url": endpoint_url,
                "model_score": best_job["score"],
                "algorithm": best_job["algorithm"],
                "deployment_status": deployment_result.get(
                    "provisioning_state", "Unknown"
                ),
                "metadata_summary": {
                    "parent_fields": len(
                        [v for v in parent_metadata.values() if v is not None]
                    ),
                    "model_fields": len(
                        [v for v in best_model_metadata.values() if v is not None]
                    ),
                },
            }

        except Exception as e:
            logger.error(f"Deployment failed: {str(e)}")
            raise AzureMLClientError(
                f"Failed to deploy best model from experiment {experiment_name}: {str(e)}"
            )

    def deploy_registered_model(
        self,
        model_reference: str,
        endpoint_name: str,
        deployment_name: str,
        instance_type: str = "Standard_DS3_v2",
        instance_count: int = 1,
        traffic_percentage: int = 100,
    ) -> Dict[str, Any]:
        """Deploy a registered MLflow model to an endpoint."""
        logger.info(f"Deploying model {model_reference} to endpoint {endpoint_name}")

        deployment = ManagedOnlineDeployment(
            name=deployment_name,
            endpoint_name=endpoint_name,
            model=model_reference,
            instance_type=instance_type,
            instance_count=instance_count,
        )

        try:
            created_deployment = self.endpoint_service.handle_azure_operation(
                f"deploy_model_{deployment_name}",
                self.endpoint_service.client.online_deployments.begin_create_or_update,
                deployment,
            )
            logger.info(f"✅ MLflow deployment created: {created_deployment.name}")

            # Set traffic allocation if specified
            if traffic_percentage > 0:
                logger.info(
                    f"Setting traffic to {traffic_percentage}% for new deployment..."
                )
                self.endpoint_service.update_endpoint_traffic(
                    endpoint_name, {deployment_name: traffic_percentage}
                )
                logger.info("✅ Traffic allocation updated")

            return {
                "name": created_deployment.name,
                "endpoint_name": created_deployment.endpoint_name,
                "model": created_deployment.model,
                "instance_type": created_deployment.instance_type,
                "instance_count": created_deployment.instance_count,
                "provisioning_state": created_deployment.provisioning_state,
            }

        except Exception as e:
            raise AzureMLClientError(
                f"Failed to deploy model {model_reference}: {str(e)}"
            )
