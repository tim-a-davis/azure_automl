from uuid import uuid4
from typing import List, Any, Dict
from azure.identity import ClientSecretCredential
from azure.ai.ml import MLClient, command
from azure.ai.ml.entities import Data, OnlineDeployment
import tempfile
import os

from ..config import settings
from ..schemas.dataset import Dataset as DatasetSchema
from ..schemas.experiment import Experiment as ExperimentSchema
from ..schemas.run import Run as RunSchema
from ..schemas.model import Model as ModelSchema
from ..schemas.endpoint import Endpoint as EndpointSchema

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
            resource_group=settings.azure_ml_resource_group,
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

    def upload_dataset(self, filename: str, data: bytes) -> DatasetSchema:
        """Upload a dataset to the workspace and return its registered metadata."""
        tmp_dir = tempfile.mkdtemp()
        file_path = os.path.join(tmp_dir, filename)
        with open(file_path, "wb") as f:
            f.write(data)

        dataset = Data(name=filename, path=file_path, type="uri_file")
        created = self.client.data.create_or_update(dataset)
        info: Dict[str, Any] = getattr(created, "_to_dict", lambda: {})()

        return DatasetSchema(
            id=getattr(created, "id", uuid4()),
            tenant_id="",
            name=info.get("name", filename),
            version=info.get("version"),
            storage_uri=info.get("path", file_path),
        )

    def start_experiment(self, config: ExperimentSchema) -> RunSchema:
        """Launch an experiment/job in Azure ML and return the run information."""
        job = command(name=f"job-{uuid4()}", command="echo experiment")
        submitted = self.client.jobs.create_or_update(job)

        ctx = getattr(submitted, "creation_context", None)
        queued = getattr(ctx, "created_at", None) if ctx else None

        return RunSchema(
            id=getattr(submitted, "id", uuid4()),
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
