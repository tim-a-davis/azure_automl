import os
import tempfile
import time
from typing import Any, Dict, List, Optional
from uuid import uuid4

from azure.ai.ml import Input, MLClient, automl, command
from azure.ai.ml.constants import AssetTypes
from azure.ai.ml.entities import (
    Data,
    ManagedOnlineDeployment,
    ManagedOnlineEndpoint,
    Model,
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

    def upload_dataset(self, dataset_name: str, data: bytes) -> dict:
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

        return {
            "id": str(uuid4()),  # Generate a new UUID for our internal tracking
            "name": info.get("name", dataset_name),
            "version": info.get("version"),
            "storage_uri": info.get("path", tmp_dir),
        }

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
            user_id=config.user_id,
            experiment_id=config.id,  # Set the experiment_id from the config
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
                "user_id": str(uuid4()),  # Will be set by the calling route
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
                "user_id": str(uuid4()),  # Will be set by the calling route
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
                "user_id": str(uuid4()),  # Will be set by the calling route
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

    # =====================================================
    # Model Discovery and Registration Methods (from deploy_best_model.py)
    # =====================================================

    def get_experiment_child_jobs_with_scores(self, experiment_name: str) -> List[Dict]:
        """Get all child jobs and their scores from an AutoML experiment."""
        print(f"Getting child jobs for experiment: {experiment_name}")

        child_jobs = list(self.client.jobs.list(parent_job_name=experiment_name))
        print(f"Found {len(child_jobs)} child jobs")

        jobs_with_scores = []

        for job in child_jobs:
            job_info = {
                "name": job.name,
                "status": job.status,
                "algorithm": "unknown",
                "score": None,
                "metrics": {},
                "job_type": getattr(job, "type", None),
            }

            # Extract score from properties - look for multiple possible score fields
            if hasattr(job, "properties") and job.properties:
                for key, value in job.properties.items():
                    key_lower = key.lower()

                    # Look for primary score/accuracy metrics
                    if key_lower in ["score", "accuracy", "primary_metric_score"]:
                        try:
                            job_info["score"] = float(value)
                        except (ValueError, TypeError):
                            pass

                    # Look for algorithm information
                    if key_lower in ["algorithm", "model_name", "estimator"]:
                        job_info["algorithm"] = str(value)

                    # Look for other performance metrics
                    metric_keywords = [
                        "accuracy",
                        "precision",
                        "recall",
                        "f1",
                        "auc",
                        "roc_auc",
                        "weighted_accuracy",
                        "macro_precision",
                        "macro_recall",
                        "macro_f1",
                        "micro_precision",
                        "micro_recall",
                        "micro_f1",
                        "matthews_correlation",
                        "log_loss",
                        "norm_macro_recall",
                        "average_precision_score_weighted",
                        "precision_score_weighted",
                        "recall_score_weighted",
                        "f1_score_weighted",
                    ]

                    if any(metric in key_lower for metric in metric_keywords):
                        try:
                            job_info["metrics"][key] = float(value)
                            # If we don't have a primary score yet, use accuracy or auc as fallback
                            if job_info["score"] is None and key_lower in [
                                "accuracy",
                                "auc",
                                "roc_auc",
                            ]:
                                job_info["score"] = float(value)
                        except (ValueError, TypeError):
                            pass

                    # Store other interesting properties
                    interesting_props = [
                        "run_algorithm",
                        "run_preprocessor",
                        "model_size",
                        "training_time",
                        "prediction_time",
                        "model_memory_size",
                        "data_transformer",
                    ]
                    if any(prop in key_lower for prop in interesting_props):
                        job_info["metrics"][key] = str(value)

            # Extract additional metadata from job attributes
            if hasattr(job, "tags") and job.tags:
                for tag_key, tag_value in job.tags.items():
                    if tag_key.lower() in ["algorithm", "model_name"] and tag_value:
                        job_info["algorithm"] = str(tag_value)

            # Only include jobs with scores (these are the model training jobs)
            if job_info["score"] is not None:
                jobs_with_scores.append(job_info)

        # Sort by score (highest first for accuracy-based metrics)
        jobs_with_scores.sort(key=lambda x: x["score"], reverse=True)

        print(f"Found {len(jobs_with_scores)} jobs with scores")

        # Print summary of top jobs
        if jobs_with_scores:
            print("\nTop performing jobs:")
            for i, job in enumerate(jobs_with_scores[:3], 1):
                metrics_summary = []
                if job["metrics"]:
                    for k, v in list(job["metrics"].items())[
                        :3
                    ]:  # Show first 3 metrics
                        if isinstance(v, (int, float)):
                            metrics_summary.append(f"{k}: {v:.4f}")
                        else:
                            metrics_summary.append(f"{k}: {v}")
                metrics_str = (
                    " | ".join(metrics_summary)
                    if metrics_summary
                    else "No additional metrics"
                )
                print(
                    f"  {i}. {job['name']} - Score: {job['score']:.4f} - Algorithm: {job['algorithm']} - {metrics_str}"
                )

        return jobs_with_scores

    def extract_parent_job_metadata(self, parent_job_name: str) -> Dict:
        """Extract metadata from the parent AutoML job."""
        print(f"Extracting metadata from parent job: {parent_job_name}")

        try:
            parent_job = self.client.jobs.get(parent_job_name)

            metadata = {
                "experiment_name": parent_job_name,
                "task_type": None,
                "primary_metric": None,
                "dataset_name": None,
                "dataset_version": None,
                "target_column": None,
                "training_data_path": None,
                "compute_target": None,
                "max_trials": None,
                "timeout_minutes": None,
                "enable_early_termination": None,
                "job_status": getattr(parent_job, "status", None),
                "creation_context": None,
            }

            # Extract basic job information
            if hasattr(parent_job, "task") and parent_job.task:
                task = parent_job.task

                # Task type
                if hasattr(task, "type"):
                    metadata["task_type"] = str(task.type)

                # Primary metric
                if hasattr(task, "primary_metric"):
                    metadata["primary_metric"] = str(task.primary_metric)

                # Training data and target column
                if hasattr(task, "training_data"):
                    training_data = task.training_data
                    if hasattr(training_data, "path"):
                        metadata["training_data_path"] = str(training_data.path)
                    # Try to extract dataset name from path or other attributes
                    if hasattr(training_data, "name"):
                        metadata["dataset_name"] = str(training_data.name)
                    elif hasattr(training_data, "path") and training_data.path:
                        # Try to extract dataset name from path
                        path_str = str(training_data.path)
                        if "azureml://datastores" in path_str:
                            parts = path_str.split("/")
                            for i, part in enumerate(parts):
                                if part == "paths" and i + 1 < len(parts):
                                    dataset_part = parts[i + 1]
                                    if dataset_part and not dataset_part.endswith(
                                        ".csv"
                                    ):
                                        metadata["dataset_name"] = dataset_part
                                    break

                # Target column
                if hasattr(task, "target_column_name"):
                    metadata["target_column"] = str(task.target_column_name)

            # Extract limits information
            if hasattr(parent_job, "limits") and parent_job.limits:
                limits = parent_job.limits
                if hasattr(limits, "max_trials"):
                    metadata["max_trials"] = limits.max_trials
                if hasattr(limits, "timeout_minutes"):
                    metadata["timeout_minutes"] = limits.timeout_minutes
                if hasattr(limits, "enable_early_termination"):
                    metadata["enable_early_termination"] = (
                        limits.enable_early_termination
                    )

            # Compute target
            if hasattr(parent_job, "compute") and parent_job.compute:
                metadata["compute_target"] = str(parent_job.compute)

            # Creation context (user info)
            if hasattr(parent_job, "creation_context") and parent_job.creation_context:
                context = parent_job.creation_context
                if hasattr(context, "created_by"):
                    metadata["creation_context"] = str(context.created_by)

            # Extract additional properties
            if hasattr(parent_job, "properties") and parent_job.properties:
                for key, value in parent_job.properties.items():
                    if key not in metadata and value is not None:
                        metadata[f"property_{key}"] = str(value)

            # Extract tags
            if hasattr(parent_job, "tags") and parent_job.tags:
                for key, value in parent_job.tags.items():
                    if key not in metadata and value is not None:
                        metadata[f"tag_{key}"] = str(value)

            print(
                f"Extracted parent job metadata: {len([k for k, v in metadata.items() if v is not None])} fields"
            )
            return metadata

        except Exception as e:
            print(f"Warning: Could not extract parent job metadata: {e}")
            return {
                "experiment_name": parent_job_name,
                "task_type": "unknown",
                "primary_metric": "unknown",
            }

    def extract_best_model_metadata(
        self, best_job_name: str, best_job_info: Dict
    ) -> Dict:
        """Extract detailed metadata from the best performing model job."""
        print(f"Extracting detailed metadata from best job: {best_job_name}")

        try:
            best_job = self.client.jobs.get(best_job_name)

            metadata = {
                "best_job_name": best_job_name,
                "best_score": best_job_info.get("score"),
                "algorithm": best_job_info.get("algorithm", "unknown"),
                "job_status": getattr(best_job, "status", None),
                "model_explanation_enabled": None,
                "feature_importance_available": None,
            }

            # Extract all metrics from the job info
            if "metrics" in best_job_info:
                for metric_name, metric_value in best_job_info["metrics"].items():
                    metadata[f"metric_{metric_name.lower()}"] = metric_value

            # Extract additional properties from the job
            if hasattr(best_job, "properties") and best_job.properties:
                for key, value in best_job.properties.items():
                    if key not in metadata and value is not None:
                        # Convert specific known properties
                        if key.lower() in [
                            "algorithm",
                            "model_explanation",
                            "feature_importance",
                        ]:
                            metadata[key.lower()] = str(value)
                        else:
                            metadata[f"model_property_{key}"] = str(value)

            # Extract outputs information
            if hasattr(best_job, "outputs") and best_job.outputs:
                outputs = best_job.outputs
                if hasattr(outputs, "keys"):
                    metadata["available_outputs"] = ",".join(outputs.keys())

            # Extract job tags
            if hasattr(best_job, "tags") and best_job.tags:
                for key, value in best_job.tags.items():
                    if key not in metadata and value is not None:
                        metadata[f"model_tag_{key}"] = str(value)

            print(
                f"Extracted best model metadata: {len([k for k, v in metadata.items() if v is not None])} fields"
            )
            return metadata

        except Exception as e:
            print(f"Warning: Could not extract best model metadata: {e}")
            return {
                "best_job_name": best_job_name,
                "best_score": best_job_info.get("score"),
                "algorithm": best_job_info.get("algorithm", "unknown"),
            }

    def create_model_tags_from_metadata(
        self, parent_metadata: Dict, model_metadata: Dict
    ) -> Dict[str, str]:
        """Create focused tags with the most important metadata fields."""
        tags = {
            "created_by": "automl_service",
            "deployment_timestamp": str(int(time.time())),
        }

        # Top 8 most important tags from experiment and model metadata
        important_fields = [
            ("task_type", parent_metadata.get("task_type")),
            ("primary_metric", parent_metadata.get("primary_metric")),
            ("dataset_name", parent_metadata.get("dataset_name")),
            ("target_column", parent_metadata.get("target_column")),
            ("algorithm", model_metadata.get("algorithm")),
            ("best_score", model_metadata.get("best_score")),
            ("job_status", parent_metadata.get("job_status")),
            ("source_experiment", parent_metadata.get("experiment_name")),
        ]

        # Add the important fields as tags (only if they have values)
        for tag_name, value in important_fields:
            if value is not None:
                # Format the value appropriately
                if isinstance(value, float):
                    tag_value = f"{value:.4f}"
                else:
                    tag_value = str(value)[:256]  # Azure ML tag limit
                tags[tag_name] = tag_value

        return tags

    def format_model_description(
        self, parent_metadata: Dict, model_metadata: Dict
    ) -> str:
        """Create comprehensive description for the registered model."""
        desc_parts = [
            f"AutoML model from experiment '{parent_metadata.get('experiment_name', 'unknown')}'",
        ]

        if parent_metadata.get("task_type"):
            desc_parts.append(f"Task: {parent_metadata['task_type']}")

        if model_metadata.get("algorithm"):
            desc_parts.append(f"Algorithm: {model_metadata['algorithm']}")

        if model_metadata.get("best_score"):
            metric_name = parent_metadata.get("primary_metric", "score")
            desc_parts.append(f"{metric_name}: {model_metadata['best_score']:.4f}")

        if parent_metadata.get("dataset_name"):
            desc_parts.append(f"Dataset: {parent_metadata['dataset_name']}")

        if parent_metadata.get("target_column"):
            desc_parts.append(f"Target: {parent_metadata['target_column']}")

        return " | ".join(desc_parts)

    def register_model_from_job(
        self,
        job_name: str,
        model_name: str,
        parent_metadata: Dict,
        best_model_metadata: Dict,
    ) -> str:
        """Register a model from a job's outputs using the complete AutoML artifacts."""
        print(f"Registering model from job: {job_name}")

        # The Azure ML model URI must match this exact regex format:
        subscription_id = settings.azure_subscription_id
        resource_group = settings.azure_ml_resource_group
        workspace_name = settings.azure_ml_workspace

        errors = []

        # Create focused tags and description
        tags = self.create_model_tags_from_metadata(
            parent_metadata, best_model_metadata
        )
        description = self.format_model_description(
            parent_metadata, best_model_metadata
        )

        # Try approach 1: Full datastore path with subscription info to MLflow model
        try:
            model_path = f"azureml://subscriptions/{subscription_id}/resourceGroups/{resource_group}/workspaces/{workspace_name}/datastores/workspaceartifactstore/paths/ExperimentRun/dcid.{job_name}/outputs/mlflow-model"

            print(f"Trying full datastore path to MLflow model: {model_path}")

            model = Model(
                name=model_name,
                path=model_path,
                description=description,
                type="mlflow_model",
                tags=tags,
            )

            registered_model = self.client.models.create_or_update(model)
            model_reference = f"{registered_model.name}:{registered_model.version}"
            print(f"✅ MLflow model registered successfully: {model_reference}")
            print(f"📊 Model registered with {len(tags)} metadata tags")
            return model_reference

        except Exception as e:
            print(f"Full MLflow path failed: {e}")
            errors.append(f"Full MLflow datastore path: {e}")

        # Try approach 2: Full datastore path to complete outputs directory
        try:
            model_path = f"azureml://subscriptions/{subscription_id}/resourceGroups/{resource_group}/workspaces/{workspace_name}/datastores/workspaceartifactstore/paths/ExperimentRun/dcid.{job_name}/outputs"

            print(f"Trying full datastore path to outputs: {model_path}")

            tags_with_note = tags.copy()
            tags_with_note["contains_mlflow_model"] = "true"

            model = Model(
                name=model_name,
                path=model_path,
                description=f"{description} - complete outputs with MLflow artifacts",
                type="custom_model",
                tags=tags_with_note,
            )

            registered_model = self.client.models.create_or_update(model)
            model_reference = f"{registered_model.name}:{registered_model.version}"
            print(f"✅ Complete outputs model registered: {model_reference}")
            print(f"📊 Model registered with {len(tags_with_note)} metadata tags")
            return model_reference

        except Exception as e:
            print(f"Full outputs path failed: {e}")
            errors.append(f"Full outputs datastore path: {e}")

        print("All registration attempts failed:")
        for error in errors:
            print(f"  {error}")
        raise Exception(
            f"Could not register model from job {job_name}. All registration methods failed."
        )

    def create_or_get_endpoint_with_metadata(
        self, endpoint_name: str, metadata: Optional[Dict] = None
    ) -> str:
        """Create endpoint if it doesn't exist, otherwise return existing."""
        try:
            endpoint = self.client.online_endpoints.get(endpoint_name)
            print(f"Using existing endpoint: {endpoint_name}")
            return endpoint_name
        except Exception:
            print(f"Creating new endpoint: {endpoint_name}")

            tags = {
                "created_by": "automl_service",
                "purpose": "automl_model_deployment",
            }

            # Add metadata to tags if provided
            if metadata:
                for key, value in metadata.items():
                    if value is not None and len(tags) < 10:  # Azure ML limit
                        tag_value = str(value)[:256]  # Azure ML tag value limit
                        tags[key] = tag_value

            endpoint = ManagedOnlineEndpoint(
                name=endpoint_name,
                description=f"AutoML model endpoint - {endpoint_name}",
                auth_mode="key",
                tags=tags,
            )

            created_endpoint = self.client.online_endpoints.begin_create_or_update(
                endpoint
            ).result()
            print(f"Endpoint created: {created_endpoint.name}")
            return created_endpoint.name

    # =====================================================
    # Deployment Orchestration Methods
    # =====================================================

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
        print(f"Deploying best model from experiment: {experiment_name}")

        try:
            # Extract parent job metadata first
            parent_metadata = self.extract_parent_job_metadata(experiment_name)

            # Get child jobs with scores
            jobs_with_scores = self.get_experiment_child_jobs_with_scores(
                experiment_name
            )

            if not jobs_with_scores:
                raise Exception(
                    f"No jobs with scores found for experiment {experiment_name}"
                )

            # Get the best job and extract its metadata
            best_job = jobs_with_scores[0]
            best_model_metadata = self.extract_best_model_metadata(
                best_job["name"], best_job
            )

            print(
                f"Best model found: {best_job['name']} with score {best_job['score']:.4f}"
            )

            # Register the model with comprehensive metadata
            model_name = f"automl-best-{experiment_name.replace('_', '-')}"
            model_reference = self.register_model_from_job(
                best_job["name"], model_name, parent_metadata, best_model_metadata
            )

            # Create or get endpoint with metadata
            endpoint_metadata = {
                "source_experiment": experiment_name,
                "model_algorithm": best_model_metadata.get("algorithm"),
                "model_score": str(best_model_metadata.get("best_score", "")),
            }
            actual_endpoint_name = self.create_or_get_endpoint_with_metadata(
                endpoint_name, endpoint_metadata
            )

            # Generate deployment name if not provided
            if deployment_name is None:
                deployment_name = f"deployment-{uuid4().hex[:8]}"

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
            endpoint = self.client.online_endpoints.get(actual_endpoint_name)
            endpoint_url = getattr(endpoint, "scoring_uri", "Not available")

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
            print(f"Deployment failed: {str(e)}")
            raise Exception(
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
        print(f"Deploying model {model_reference} to endpoint {endpoint_name}")

        deployment = ManagedOnlineDeployment(
            name=deployment_name,
            endpoint_name=endpoint_name,
            model=model_reference,  # MLflow model with all artifacts
            instance_type=instance_type,
            instance_count=instance_count,
            # No need to specify environment or code_configuration
            # MLflow model format includes everything needed
        )

        try:
            created_deployment = self.client.online_deployments.begin_create_or_update(
                deployment
            ).result()
            print(f"✅ MLflow deployment created: {created_deployment.name}")

            # Set traffic allocation if specified
            if traffic_percentage > 0:
                print(f"Setting traffic to {traffic_percentage}% for new deployment...")
                endpoint = self.client.online_endpoints.get(endpoint_name)
                endpoint.traffic = {deployment_name: traffic_percentage}
                self.client.online_endpoints.begin_create_or_update(endpoint).result()
                print("✅ Traffic allocation updated")

            return {
                "name": created_deployment.name,
                "endpoint_name": created_deployment.endpoint_name,
                "model": created_deployment.model,
                "instance_type": created_deployment.instance_type,
                "instance_count": created_deployment.instance_count,
                "provisioning_state": created_deployment.provisioning_state,
            }

        except Exception as e:
            raise Exception(f"Failed to deploy model {model_reference}: {str(e)}")

    def get_deployment_status(
        self, endpoint_name: str, deployment_name: str
    ) -> Dict[str, Any]:
        """Get the status of a specific deployment."""
        try:
            deployment = self.client.online_deployments.get(
                name=deployment_name, endpoint_name=endpoint_name
            )
            return {
                "name": deployment.name,
                "endpoint_name": deployment.endpoint_name,
                "provisioning_state": deployment.provisioning_state,
                "model": deployment.model,
                "instance_type": getattr(deployment, "instance_type", None),
                "instance_count": getattr(deployment, "instance_count", None),
                "ready_replica_count": getattr(deployment, "ready_replica_count", None),
            }
        except Exception as e:
            raise Exception(f"Failed to get deployment status: {str(e)}")

    def get_deployment_metrics(
        self, endpoint_name: str, deployment_name: str
    ) -> Dict[str, Any]:
        """Get performance metrics for a deployment (placeholder for future implementation)."""
        # This would integrate with Azure Monitor or other metrics services
        # For now, return basic deployment information
        try:
            deployment_status = self.get_deployment_status(
                endpoint_name, deployment_name
            )
            endpoint = self.client.online_endpoints.get(endpoint_name)

            return {
                "deployment_name": deployment_name,
                "endpoint_name": endpoint_name,
                "status": deployment_status.get("provisioning_state"),
                "ready_replicas": deployment_status.get("ready_replica_count", 0),
                "total_replicas": deployment_status.get("instance_count", 0),
                "endpoint_url": getattr(endpoint, "scoring_uri", None),
                "traffic_percentage": endpoint.traffic.get(deployment_name, 0)
                if endpoint.traffic
                else 0,
                "last_updated": time.time(),
                # Placeholder for actual metrics that would come from monitoring
                "requests_per_minute": None,
                "average_latency_ms": None,
                "error_rate_percent": None,
            }
        except Exception as e:
            raise Exception(f"Failed to get deployment metrics: {str(e)}")
