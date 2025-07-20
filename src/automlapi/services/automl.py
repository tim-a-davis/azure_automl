"""Refactored Azure AutoML service with separated concerns."""

from typing import List, Dict, Any, Optional

from ..schemas.dataset import Dataset as DatasetSchema
from ..schemas.endpoint import Endpoint as EndpointSchema
from ..schemas.experiment import Experiment as ExperimentSchema
from ..schemas.model import Model as ModelSchema
from ..schemas.run import Run as RunSchema

from .dataset_service import DatasetService
from .experiment_service import ExperimentService
from .endpoint_service import EndpointService
from .model_service import ModelService
from .deployment_service import DeploymentService


class AzureAutoMLService:
    """
    Refactored Azure AutoML service with separated concerns.
    
    This service acts as a facade over specialized services for different domains:
    - DatasetService: Dataset upload and management
    - ExperimentService: Experiment and job management
    - EndpointService: Endpoint and deployment management
    - ModelService: Model registration and management
    - DeploymentService: Deployment orchestration
    """
    
    def __init__(self):
        self.datasets = DatasetService()
        self.experiments = ExperimentService()
        self.endpoints = EndpointService()
        self.models = ModelService()
        self.deployments = DeploymentService()
    
    # ========================================
    # Dataset Methods
    # ========================================
    
    def list_datasets(self) -> List[DatasetSchema]:
        """List all datasets from Azure ML."""
        return self.datasets.list_datasets()
    
    def upload_dataset(self, dataset_name: str, data: bytes) -> Dict[str, Any]:
        """Upload a dataset to Azure ML as MLTable format."""
        return self.datasets.upload_dataset(dataset_name, data)
    
    # ========================================
    # Experiment and Run Methods
    # ========================================
    
    def list_experiments(self) -> List[ExperimentSchema]:
        """List all experiments (jobs) from Azure ML."""
        return self.experiments.list_experiments()
    
    def list_runs(self) -> List[RunSchema]:
        """List all runs (jobs) from Azure ML."""
        return self.experiments.list_runs()
    
    def start_experiment(self, config: ExperimentSchema) -> RunSchema:
        """Launch an AutoML job using serverless compute."""
        return self.experiments.start_experiment(config)
    
    def get_run_metrics(self, run_id: str) -> Dict[str, Any]:
        """Get metrics for a specific run."""
        return self.experiments.get_run_metrics(run_id)
    
    def stream_run_logs(self, run_id: str):
        """Yield log lines for a running job."""
        return self.experiments.stream_run_logs(run_id)
    
    def get_experiment_child_jobs_with_scores(self, experiment_name: str) -> List[Dict[str, Any]]:
        """Get all child jobs and their scores from an AutoML experiment."""
        return self.experiments.get_child_jobs_with_scores(experiment_name)
    
    def extract_parent_job_metadata(self, parent_job_name: str) -> Dict[str, Any]:
        """Extract metadata from the parent AutoML job."""
        return self.experiments.extract_parent_job_metadata(parent_job_name)
    
    # ========================================
    # Model Methods
    # ========================================
    
    def list_models(self) -> List[ModelSchema]:
        """List all models from Azure ML."""
        return self.models.list_models()
    
    def download_model(self, model_id: str) -> bytes:
        """Download a model package and return its bytes."""
        return self.models.download_model(model_id)
    
    def register_model_from_job(
        self,
        job_name: str,
        model_name: str,
        parent_metadata: Dict[str, Any],
        best_model_metadata: Dict[str, Any],
    ) -> str:
        """Register a model from a job's outputs."""
        return self.models.register_model_from_job(
            job_name, model_name, parent_metadata, best_model_metadata
        )
    
    def extract_best_model_metadata(
        self, 
        best_job_name: str, 
        best_job_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract detailed metadata from the best performing model job."""
        return self.models.extract_best_model_metadata(best_job_name, best_job_info)
    
    def create_model_tags_from_metadata(
        self, 
        parent_metadata: Dict[str, Any], 
        model_metadata: Dict[str, Any]
    ) -> Dict[str, str]:
        """Create focused tags with the most important metadata fields."""
        return self.models.create_model_tags_from_metadata(parent_metadata, model_metadata)
    
    def format_model_description(
        self, 
        parent_metadata: Dict[str, Any], 
        model_metadata: Dict[str, Any]
    ) -> str:
        """Create comprehensive description for the registered model."""
        return self.models.format_model_description(parent_metadata, model_metadata)
    
    # ========================================
    # Endpoint Methods
    # ========================================
    
    def list_endpoints(self) -> List[EndpointSchema]:
        """List all online endpoints from Azure ML."""
        return self.endpoints.list_endpoints()
    
    def create_endpoint(
        self, 
        endpoint_name: str, 
        description: str = None, 
        tags: Dict[str, str] = None
    ) -> EndpointSchema:
        """Create an Azure ML online endpoint."""
        return self.endpoints.create_endpoint(endpoint_name, description, tags)
    
    def get_endpoint(self, endpoint_name: str) -> EndpointSchema:
        """Get an Azure ML online endpoint by name."""
        return self.endpoints.get_endpoint(endpoint_name)
    
    def update_endpoint(
        self, 
        endpoint_name: str, 
        description: str = None, 
        tags: Dict[str, str] = None
    ) -> EndpointSchema:
        """Update an Azure ML online endpoint."""
        return self.endpoints.update_endpoint(endpoint_name, description, tags)
    
    def delete_endpoint(self, endpoint_name: str) -> bool:
        """Delete an Azure ML online endpoint."""
        return self.endpoints.delete_endpoint(endpoint_name)
    
    def create_deployment(
        self,
        endpoint_name: str,
        deployment_name: str,
        model_name: str,
        model_version: str = None,
        instance_type: str = "Standard_DS3_v2",
        instance_count: int = 1,
        traffic_percentage: int = 0,
    ) -> Dict[str, Any]:
        """Create a deployment for an Azure ML online endpoint."""
        return self.endpoints.create_deployment(
            endpoint_name, deployment_name, model_name, model_version,
            instance_type, instance_count, traffic_percentage
        )
    
    def update_endpoint_traffic(
        self, 
        endpoint_name: str, 
        traffic_allocation: Dict[str, int]
    ) -> Dict[str, int]:
        """Update traffic allocation for an endpoint."""
        return self.endpoints.update_endpoint_traffic(endpoint_name, traffic_allocation)
    
    def list_endpoint_deployments(self, endpoint_name: str) -> List[Dict[str, Any]]:
        """List all deployments for a specific endpoint."""
        return self.endpoints.list_endpoint_deployments(endpoint_name)
    
    def get_deployment_status(
        self, 
        endpoint_name: str, 
        deployment_name: str
    ) -> Dict[str, Any]:
        """Get the status of a specific deployment."""
        return self.endpoints.get_deployment_status(endpoint_name, deployment_name)
    
    def get_deployment_metrics(
        self, 
        endpoint_name: str, 
        deployment_name: str
    ) -> Dict[str, Any]:
        """Get performance metrics for a deployment."""
        return self.endpoints.get_deployment_metrics(endpoint_name, deployment_name)
    
    def create_or_get_endpoint_with_metadata(
        self, 
        endpoint_name: str, 
        metadata: Dict[str, Any] = None
    ) -> str:
        """Create endpoint if it doesn't exist, otherwise return existing."""
        return self.endpoints.create_or_get_endpoint_with_metadata(endpoint_name, metadata)
    
    # ========================================
    # Deployment Orchestration Methods
    # ========================================
    
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
        return self.deployments.deploy_best_model_from_experiment(
            experiment_name, endpoint_name, deployment_name,
            instance_type, instance_count, traffic_percentage
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
        return self.deployments.deploy_registered_model(
            model_reference, endpoint_name, deployment_name,
            instance_type, instance_count, traffic_percentage
        )
    
    # ========================================
    # Legacy Methods (Deprecated/Removed)
    # ========================================
    
    # The following methods from the original service have been removed as they
    # were either unused, duplicated functionality, or mixed concerns:
    
    # - deploy_model() - replaced by deploy_registered_model()
    # - safe_rollout() - basic traffic management, can be implemented via update_endpoint_traffic()
    # - swap_traffic() - basic traffic management, can be implemented via update_endpoint_traffic() 
    # - sync_costs() - dummy implementation, not actually used
    # - purge_artifacts() - maintenance operation, can be separate utility
    # - rotate_credentials() - infrastructure concern, should be handled at app level
    #
    # These methods can be re-added if needed, but the current codebase analysis
    # suggests they are not actively used.
