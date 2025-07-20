"""Core Azure ML client wrapper with common functionality."""

import logging
from typing import Any, Dict
from uuid import uuid4

from azure.ai.ml import MLClient
from azure.identity import ClientSecretCredential

from ..config import settings

logger = logging.getLogger(__name__)


class AzureMLClientError(Exception):
    """Base exception for Azure ML client operations."""

    pass


class AzureMLClient:
    """Wrapper around Azure ML client with common utilities."""

    def __init__(self):
        """Initialize the Azure ML client with service principal authentication."""
        try:
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
        except Exception as e:
            logger.error(f"Failed to initialize Azure ML client: {e}")
            raise AzureMLClientError(f"Failed to initialize Azure ML client: {e}")

    def generate_uuid(self) -> str:
        """Generate a UUID string for internal tracking."""
        return str(uuid4())

    def safe_getattr(self, obj: Any, attr: str, default: Any = None) -> Any:
        """Safely get attribute from object with default fallback."""
        return getattr(obj, attr, default)

    def build_model_uri(self, job_name: str, path_suffix: str = "") -> str:
        """Build standardized Azure ML model URI."""
        subscription_id = settings.azure_subscription_id
        resource_group = settings.azure_ml_resource_group
        workspace_name = settings.azure_ml_workspace

        base_path = (
            f"azureml://subscriptions/{subscription_id}/resourceGroups/{resource_group}/"
            f"workspaces/{workspace_name}/datastores/workspaceartifactstore/paths/"
            f"ExperimentRun/dcid.{job_name}/outputs"
        )

        return f"{base_path}{path_suffix}" if path_suffix else base_path

    def create_tags(self, **kwargs) -> Dict[str, str]:
        """Create standardized tags with common fields."""
        tags = {
            "created_by": "automl_service",
            "deployment_timestamp": str(int(__import__("time").time())),
        }

        # Add provided kwargs as tags, filtering None values and limiting length
        for key, value in kwargs.items():
            if value is not None and len(tags) < 10:  # Azure ML limit
                tag_value = str(value)[:256]  # Azure ML tag value limit
                tags[key] = tag_value

        return tags

    def handle_azure_operation(
        self, operation_name: str, operation_func, *args, **kwargs
    ):
        """Generic handler for Azure ML operations with consistent error handling."""
        try:
            logger.info(f"Starting Azure ML operation: {operation_name}")
            result = operation_func(*args, **kwargs)

            # Handle operations that return pollers
            if hasattr(result, "result"):
                result = result.result()

            logger.info(f"Completed Azure ML operation: {operation_name}")
            return result

        except Exception as e:
            error_msg = f"Azure ML operation '{operation_name}' failed: {str(e)}"
            logger.error(error_msg)
            raise AzureMLClientError(error_msg)
