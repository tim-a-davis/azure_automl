import os
import tempfile
from typing import Any, Dict, List
from uuid import uuid4

from azure.ai.ml import Input, MLClient, automl, command
from azure.ai.ml.constants import AssetTypes
from azure.ai.ml.entities import (
    Data,
    ManagedOnlineDeployment,
    ManagedOnlineEndpoint,
    OnlineDeployment,
)
from azure.identity import ClientSecretCredential

from ..config import settings
from ..schemas.dataset import Dataset as DatasetSchema
from ..schemas.endpoint import Endpoint as EndpointSchema
from ..schemas.experiment import Experiment as ExperimentSchema
from ..schemas.model import Model as ModelSchema
from ..schemas.run import Run as RunSchema


class AzureAutoMLService:
    def __init__(self):
        cred = ClientSecretCredential(
            tenant_id=settings.azure_tenant_id,
            client_id=settings.azure_client_id,
            client_secret=settings.azure_client_secret,
        )
        self.client = MLClient(
            credential=cred,
            subscription_id=settings.azure_subscription_id,
            resource_group_name=settings.azure_ml_resource_group,
            workspace_name=settings.azure_ml_workspace,
        )

    def list_datasets(self) -> List[DatasetSchema]:
        return [DatasetSchema(**d) for d in self.client.data.list()]  # type: ignore

    def list_experiments(self) -> List[ExperimentSchema]:
        return [ExperimentSchema(**e) for e in self.client.jobs.list()]  # type: ignore

    def list_runs(self) -> List[RunSchema]:
        return [RunSchema(**r) for r in self.client.jobs.list()]  # type: ignore

    def list_models(self) -> List[ModelSchema]:
        return [ModelSchema(**m) for m in self.client.models.list()]  # type: ignore

    def list_endpoints(self) -> List[EndpointSchema]:
        return [EndpointSchema(**e) for e in self.client.online_endpoints.list()]  # type: ignore

    def upload_dataset(self, dataset_name: str, data: bytes) -> DatasetSchema:
        """Upload a dataset to the workspace as MLTable format for AutoML compatibility."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Create the dataset CSV file
            csv_file_path = os.path.join(tmp_dir, "dataset.csv")
            with open(csv_file_path, "wb") as f:
                f.write(data)

            # Create MLTable YAML file for AutoML compatibility
            # This tells Azure ML how to read the CSV file as tabular data
            mltable_content = """$schema: https://azuremlschemas.azureedge.net/latest/MLTable.schema.json

paths:
  - file: ./dataset.csv
transformations:
  - read_delimited:
        delimiter: ','
        encoding: 'utf8'
        header: all_files_same_headers
"""

            mltable_path = os.path.join(tmp_dir, "MLTable")
            with open(mltable_path, "w") as f:
                f.write(mltable_content)

            # Upload the entire directory containing both CSV and MLTable files
            # This creates an mltable type asset that AutoML can consume
            dataset = Data(
                name=dataset_name,
                path=tmp_dir,
                type=AssetTypes.MLTABLE,
                description=f"MLTable dataset for {dataset_name} - AutoML compatible",
            )
            created = self.client.data.create_or_update(dataset)
            info: Dict[str, Any] = getattr(created, "_to_dict", lambda: {})()

        return DatasetSchema(
            id=str(uuid4()),  # Generate a new UUID for our internal tracking
            tenant_id="",
            name=info.get("name", dataset_name),
            version=info.get("version"),
            storage_uri=info.get("path", tmp_dir),
        )

    def _configure_job_limits(self, job, config: ExperimentSchema):
        """Configure limits for AutoML jobs using the set_limits method."""
        if hasattr(job, "set_limits"):
            job.set_limits(
                enable_early_termination=config.enable_early_termination,
                exit_score=config.exit_score,
                max_concurrent_trials=config.max_concurrent_trials,
                max_cores_per_trial=config.max_cores_per_trial,
                max_nodes=config.max_nodes,
                max_trials=config.max_trials,
                timeout_minutes=config.timeout_minutes,
                trial_timeout_minutes=config.trial_timeout_minutes,
            )

    def start_experiment(self, config: ExperimentSchema) -> RunSchema:
        """Launch an AutoML job using serverless compute and return the run information."""
        from azure.ai.ml.entities import ResourceConfiguration

        data_input = None
        if config.training_data:
            data_input = Input(type=AssetTypes.MLTABLE, path=config.training_data)

        if config.task_type == "classification":
            job = automl.classification(
                # No compute specified - uses serverless compute by default
                experiment_name="automl-experiment",
                training_data=data_input,
                target_column_name=config.target_column_name,
                primary_metric=config.primary_metric or "accuracy",
                n_cross_validations=config.n_cross_validations or 5,
            )
            # Configure limits for the job
            self._configure_job_limits(job, config)

            # Configure serverless compute resources (optional)
            if hasattr(job, "resources"):
                job.resources = ResourceConfiguration(
                    instance_type="Standard_DS3_v2",  # Cost-effective CPU instance
                    instance_count=1,
                )
        elif config.task_type == "regression":
            job = automl.regression(
                # No compute specified - uses serverless compute by default
                experiment_name="automl-experiment",
                training_data=data_input,
                target_column_name=config.target_column_name,
                primary_metric=config.primary_metric or "r2_score",
                n_cross_validations=config.n_cross_validations or 5,
            )
            # Configure limits for the job
            self._configure_job_limits(job, config)

            # Configure serverless compute resources (optional)
            if hasattr(job, "resources"):
                job.resources = ResourceConfiguration(
                    instance_type="Standard_DS3_v2",  # Cost-effective CPU instance
                    instance_count=1,
                )
        elif config.task_type == "forecasting":
            job = automl.forecasting(
                # No compute specified - uses serverless compute by default
                experiment_name="automl-experiment",
                training_data=data_input,
                target_column_name=config.target_column_name,
                primary_metric=config.primary_metric
                or "normalized_root_mean_squared_error",
                n_cross_validations=config.n_cross_validations or 5,
            )
            # Configure limits for the job
            self._configure_job_limits(job, config)

            # Configure serverless compute resources (optional)
            if hasattr(job, "resources"):
                job.resources = ResourceConfiguration(
                    instance_type="Standard_DS3_v2",  # Cost-effective CPU instance
                    instance_count=1,
                )
        else:
            # Fallback to a simple command job with serverless compute
            job = command(
                name=f"job-{uuid4()}",
                command="echo experiment",
                environment="azureml:AzureML-sklearn-1.0-ubuntu20.04-py38-cpu@latest",
            )
            job.resources = ResourceConfiguration(
                instance_type="Standard_DS3_v2", instance_count=1
            )

        submitted = self.client.jobs.create_or_update(job)

        ctx = getattr(submitted, "creation_context", None)
        queued = getattr(ctx, "created_at", None) if ctx else None

        return RunSchema(
            id=str(
                uuid4()
            ),  # Generate our own UUID for tracking since Azure ML IDs aren't UUID format
            tenant_id=config.tenant_id,
            job_name=getattr(submitted, "name", None),
            queued_at=queued,
        )

    def get_run_metrics(self, run_id: str):
        """Return metrics for a given run."""
        run = self.client.jobs.get(run_id)
        return getattr(run, "metrics", {})

    def stream_run_logs(self, run_id: str):
        """Yield log lines for a running job."""
        for line in self.client.jobs.stream(run_id):
            yield line

    def download_model(self, model_id: str):
        """Download a model package and return its bytes."""
        tmp_dir = tempfile.mkdtemp()
        self.client.models.download(name=model_id, download_path=tmp_dir)
        for root, _, files in os.walk(tmp_dir):
            for f in files:
                path = os.path.join(root, f)
                with open(path, "rb") as fp:
                    return fp.read()
        return b""

    def deploy_model(self, model_id: str):
        """Deploy a model using an online deployment."""
        deployment = OnlineDeployment(name=f"dep-{uuid4()}", model=model_id)
        poller = self.client.online_deployments.begin_create_or_update(deployment)
        result = poller.result() if hasattr(poller, "result") else poller
        return getattr(result, "properties", {})

    def safe_rollout(self, endpoint_id: str):
        """Increase blue traffic in small increments."""
        endpoint = self.client.online_endpoints.get(endpoint_id)
        traffic = getattr(endpoint, "traffic", {})
        blue = traffic.get("blue", 0)
        traffic["blue"] = min(100, blue + 10)
        endpoint.traffic = traffic
        poller = self.client.online_endpoints.begin_create_or_update(endpoint)
        result = poller.result() if hasattr(poller, "result") else poller
        return getattr(result, "traffic", traffic)

    def swap_traffic(self, endpoint_id: str):
        """Swap blue and green traffic assignments."""
        endpoint = self.client.online_endpoints.get(endpoint_id)
        traffic = getattr(endpoint, "traffic", {})
        blue, green = traffic.get("blue"), traffic.get("green")
        if blue is not None and green is not None:
            traffic["blue"], traffic["green"] = green, blue
            endpoint.traffic = traffic
            poller = self.client.online_endpoints.begin_create_or_update(endpoint)
            result = poller.result() if hasattr(poller, "result") else poller
            return getattr(result, "traffic", traffic)
        return traffic

    def sync_costs(self):
        """Return a summary of tracked job count as a dummy cost metric."""
        runs = list(self.client.jobs.list())
        return {"run_count": len(runs)}

    def purge_artifacts(self):
        """Archive datasets that have no version information."""
        for ds in self.client.data.list():
            if getattr(ds, "version", None) is None:
                self.client.data.archive(name=ds.name)
        return {"status": "completed"}

    def rotate_credentials(self):
        """Refresh the MLClient credential instance."""
        cred = ClientSecretCredential(
            tenant_id=settings.azure_tenant_id,
            client_id=settings.azure_client_id,
            client_secret=settings.azure_client_secret,
        )
        self.client = MLClient(
            credential=cred,
            subscription_id=settings.azure_subscription_id,
            resource_group=settings.azure_ml_resource_group,
            workspace_name=settings.azure_ml_workspace,
        )
        return {"status": "rotated"}

    def create_endpoint(
        self, endpoint_name: str, description: str = None, tags: Dict[str, str] = None
    ) -> EndpointSchema:
        """Create an Azure ML online endpoint."""
        endpoint = ManagedOnlineEndpoint(
            name=endpoint_name,
            description=description or f"Online endpoint {endpoint_name}",
            tags=tags or {},
            auth_mode="key",
        )

        try:
            created_endpoint = self.client.online_endpoints.begin_create_or_update(
                endpoint
            ).result()

            # Convert to our schema format
            endpoint_dict = {
                "id": str(uuid4()),  # Generate a UUID for our internal tracking
                "tenant_id": "",  # Will be set by the calling route
                "name": created_endpoint.name,
                "azure_endpoint_name": created_endpoint.name,
                "azure_endpoint_url": getattr(created_endpoint, "scoring_uri", None),
                "auth_mode": created_endpoint.auth_mode,
                "provisioning_state": created_endpoint.provisioning_state,
                "tags": created_endpoint.tags or {},
                "description": created_endpoint.description,
            }

            return EndpointSchema(**endpoint_dict)
        except Exception as e:
            raise Exception(f"Failed to create endpoint: {str(e)}")

    def get_endpoint(self, endpoint_name: str) -> EndpointSchema:
        """Get an Azure ML online endpoint by name."""
        try:
            endpoint = self.client.online_endpoints.get(endpoint_name)

            # Get deployment information
            deployments = {}
            try:
                deployment_list = list(
                    self.client.online_deployments.list(endpoint_name=endpoint_name)
                )
                for deployment in deployment_list:
                    deployments[deployment.name] = {
                        "instance_type": getattr(deployment, "instance_type", None),
                        "instance_count": getattr(deployment, "instance_count", None),
                        "model": getattr(deployment, "model", None),
                        "traffic_percentage": None,  # Will be set from endpoint traffic
                    }
            except Exception:
                # If we can't get deployments, continue without them
                pass

            # Get traffic allocation
            traffic = getattr(endpoint, "traffic", {})
            for deployment_name, percentage in traffic.items():
                if deployment_name in deployments:
                    deployments[deployment_name]["traffic_percentage"] = percentage

            endpoint_dict = {
                "id": str(uuid4()),  # Generate a UUID for our internal tracking
                "tenant_id": "",  # Will be set by the calling route
                "name": endpoint.name,
                "azure_endpoint_name": endpoint.name,
                "azure_endpoint_url": getattr(endpoint, "scoring_uri", None),
                "auth_mode": endpoint.auth_mode,
                "provisioning_state": endpoint.provisioning_state,
                "tags": endpoint.tags or {},
                "description": endpoint.description,
                "deployments": deployments,
                "traffic": traffic,
            }

            return EndpointSchema(**endpoint_dict)
        except Exception as e:
            raise Exception(f"Failed to get endpoint: {str(e)}")

    def update_endpoint(
        self, endpoint_name: str, description: str = None, tags: Dict[str, str] = None
    ) -> EndpointSchema:
        """Update an Azure ML online endpoint."""
        try:
            # Get the existing endpoint
            existing_endpoint = self.client.online_endpoints.get(endpoint_name)

            # Update the endpoint
            endpoint = ManagedOnlineEndpoint(
                name=endpoint_name,
                description=description
                if description is not None
                else existing_endpoint.description,
                tags=tags if tags is not None else existing_endpoint.tags,
                auth_mode=existing_endpoint.auth_mode,
            )

            updated_endpoint = self.client.online_endpoints.begin_create_or_update(
                endpoint
            ).result()

            endpoint_dict = {
                "id": str(uuid4()),  # Generate a UUID for our internal tracking
                "tenant_id": "",  # Will be set by the calling route
                "name": updated_endpoint.name,
                "azure_endpoint_name": updated_endpoint.name,
                "azure_endpoint_url": getattr(updated_endpoint, "scoring_uri", None),
                "auth_mode": updated_endpoint.auth_mode,
                "provisioning_state": updated_endpoint.provisioning_state,
                "tags": updated_endpoint.tags or {},
                "description": updated_endpoint.description,
            }

            return EndpointSchema(**endpoint_dict)
        except Exception as e:
            raise Exception(f"Failed to update endpoint: {str(e)}")

    def delete_endpoint(self, endpoint_name: str) -> bool:
        """Delete an Azure ML online endpoint."""
        try:
            self.client.online_endpoints.begin_delete(endpoint_name).result()
            return True
        except Exception as e:
            raise Exception(f"Failed to delete endpoint: {str(e)}")

    def create_deployment(
        self,
        endpoint_name: str,
        deployment_name: str,
        model_name: str,
        model_version: str = None,
        instance_type: str = "Standard_DS3_v2",
        instance_count: int = 1,
        traffic_percentage: int = 0,
    ):
        """Create a deployment for an Azure ML online endpoint."""
        try:
            # Get the model
            if model_version:
                model = f"{model_name}:{model_version}"
            else:
                # Get the latest version
                model_list = list(self.client.models.list(name=model_name))
                if not model_list:
                    raise Exception(f"Model {model_name} not found")
                latest_model = max(model_list, key=lambda x: int(x.version))
                model = f"{model_name}:{latest_model.version}"

            deployment = ManagedOnlineDeployment(
                name=deployment_name,
                endpoint_name=endpoint_name,
                model=model,
                instance_type=instance_type,
                instance_count=instance_count,
            )

            created_deployment = self.client.online_deployments.begin_create_or_update(
                deployment
            ).result()

            # Update traffic if specified
            if traffic_percentage > 0:
                self.update_endpoint_traffic(
                    endpoint_name, {deployment_name: traffic_percentage}
                )

            return {
                "name": created_deployment.name,
                "endpoint_name": created_deployment.endpoint_name,
                "model": created_deployment.model,
                "instance_type": created_deployment.instance_type,
                "instance_count": created_deployment.instance_count,
                "provisioning_state": created_deployment.provisioning_state,
            }
        except Exception as e:
            raise Exception(f"Failed to create deployment: {str(e)}")

    def update_endpoint_traffic(
        self, endpoint_name: str, traffic_allocation: Dict[str, int]
    ):
        """Update traffic allocation for an endpoint."""
        try:
            endpoint = self.client.online_endpoints.get(endpoint_name)
            endpoint.traffic = traffic_allocation

            updated_endpoint = self.client.online_endpoints.begin_create_or_update(
                endpoint
            ).result()
            return updated_endpoint.traffic
        except Exception as e:
            raise Exception(f"Failed to update endpoint traffic: {str(e)}")

    def list_endpoint_deployments(self, endpoint_name: str):
        """List all deployments for a specific endpoint."""
        try:
            deployments = list(
                self.client.online_deployments.list(endpoint_name=endpoint_name)
            )
            return [
                {
                    "name": d.name,
                    "endpoint_name": d.endpoint_name,
                    "model": d.model,
                    "instance_type": getattr(d, "instance_type", None),
                    "instance_count": getattr(d, "instance_count", None),
                    "provisioning_state": d.provisioning_state,
                }
                for d in deployments
            ]
        except Exception as e:
            raise Exception(f"Failed to list deployments: {str(e)}")
