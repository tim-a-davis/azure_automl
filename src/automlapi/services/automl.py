import os
import tempfile
from typing import Any, Dict, List
from uuid import uuid4

from azure.ai.ml import Input, MLClient, automl, command
from azure.ai.ml.constants import AssetTypes
from azure.ai.ml.entities import Data, OnlineDeployment
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
