"""Endpoint and deployment management service for Azure ML."""

import logging
from typing import Any, Dict, List

from azure.ai.ml.entities import ManagedOnlineDeployment, ManagedOnlineEndpoint

from ..schemas.endpoint import Endpoint as EndpointSchema
from .azure_client import AzureMLClient, AzureMLClientError

logger = logging.getLogger(__name__)


class EndpointService(AzureMLClient):
    """Service for managing endpoints and deployments in Azure ML."""

    def list_endpoints(self) -> List[EndpointSchema]:
        """List all online endpoints from Azure ML."""
        try:
            endpoints = list(self.client.online_endpoints.list())
            return [self._convert_to_schema(endpoint) for endpoint in endpoints]
        except Exception as e:
            raise AzureMLClientError(f"Failed to list endpoints: {e}")

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
            created_endpoint = self.handle_azure_operation(
                f"create_endpoint_{endpoint_name}",
                self.client.online_endpoints.begin_create_or_update,
                endpoint,
            )

            return self._convert_to_schema(created_endpoint)

        except Exception as e:
            raise AzureMLClientError(f"Failed to create endpoint {endpoint_name}: {e}")

    def get_endpoint(self, endpoint_name: str) -> EndpointSchema:
        """Get an Azure ML online endpoint by name."""
        try:
            endpoint = self.client.online_endpoints.get(endpoint_name)

            # Get deployment information
            deployments = self._get_endpoint_deployments(endpoint_name)
            traffic = self.safe_getattr(endpoint, "traffic", {})

            # Update deployment traffic percentages
            for deployment_name, percentage in traffic.items():
                if deployment_name in deployments:
                    deployments[deployment_name]["traffic_percentage"] = percentage

            schema_data = self._endpoint_to_dict(endpoint)
            schema_data.update(
                {
                    "deployments": deployments,
                    "traffic": traffic,
                }
            )

            return EndpointSchema(**schema_data)

        except Exception as e:
            raise AzureMLClientError(f"Failed to get endpoint {endpoint_name}: {e}")

    def update_endpoint(
        self, endpoint_name: str, description: str = None, tags: Dict[str, str] = None
    ) -> EndpointSchema:
        """Update an Azure ML online endpoint."""
        try:
            # Get existing endpoint
            existing_endpoint = self.client.online_endpoints.get(endpoint_name)

            # Create updated endpoint
            endpoint = ManagedOnlineEndpoint(
                name=endpoint_name,
                description=description
                if description is not None
                else existing_endpoint.description,
                tags=tags if tags is not None else existing_endpoint.tags,
                auth_mode=existing_endpoint.auth_mode,
            )

            updated_endpoint = self.handle_azure_operation(
                f"update_endpoint_{endpoint_name}",
                self.client.online_endpoints.begin_create_or_update,
                endpoint,
            )

            return self._convert_to_schema(updated_endpoint)

        except Exception as e:
            raise AzureMLClientError(f"Failed to update endpoint {endpoint_name}: {e}")

    def delete_endpoint(self, endpoint_name: str) -> bool:
        """Delete an Azure ML online endpoint."""
        try:
            self.handle_azure_operation(
                f"delete_endpoint_{endpoint_name}",
                self.client.online_endpoints.begin_delete,
                endpoint_name,
            )
            return True
        except Exception as e:
            raise AzureMLClientError(f"Failed to delete endpoint {endpoint_name}: {e}")

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
        try:
            # Get the model reference
            model = self._get_model_reference(model_name, model_version)

            deployment = ManagedOnlineDeployment(
                name=deployment_name,
                endpoint_name=endpoint_name,
                model=model,
                instance_type=instance_type,
                instance_count=instance_count,
            )

            created_deployment = self.handle_azure_operation(
                f"create_deployment_{deployment_name}",
                self.client.online_deployments.begin_create_or_update,
                deployment,
            )

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
            raise AzureMLClientError(
                f"Failed to create deployment {deployment_name}: {e}"
            )

    def update_endpoint_traffic(
        self, endpoint_name: str, traffic_allocation: Dict[str, int]
    ) -> Dict[str, int]:
        """Update traffic allocation for an endpoint."""
        try:
            endpoint = self.client.online_endpoints.get(endpoint_name)
            endpoint.traffic = traffic_allocation

            updated_endpoint = self.handle_azure_operation(
                f"update_traffic_{endpoint_name}",
                self.client.online_endpoints.begin_create_or_update,
                endpoint,
            )

            return self.safe_getattr(updated_endpoint, "traffic", traffic_allocation)

        except Exception as e:
            raise AzureMLClientError(
                f"Failed to update endpoint traffic for {endpoint_name}: {e}"
            )

    def list_endpoint_deployments(self, endpoint_name: str) -> List[Dict[str, Any]]:
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
                    "instance_type": self.safe_getattr(d, "instance_type"),
                    "instance_count": self.safe_getattr(d, "instance_count"),
                    "provisioning_state": d.provisioning_state,
                }
                for d in deployments
            ]
        except Exception as e:
            raise AzureMLClientError(
                f"Failed to list deployments for {endpoint_name}: {e}"
            )

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
                "instance_type": self.safe_getattr(deployment, "instance_type"),
                "instance_count": self.safe_getattr(deployment, "instance_count"),
                "ready_replica_count": self.safe_getattr(
                    deployment, "ready_replica_count"
                ),
            }
        except Exception as e:
            raise AzureMLClientError(
                f"Failed to get deployment status for {deployment_name}: {e}"
            )

    def get_deployment_metrics(
        self, endpoint_name: str, deployment_name: str
    ) -> Dict[str, Any]:
        """Get performance metrics for a deployment."""
        try:
            deployment_status = self.get_deployment_status(
                endpoint_name, deployment_name
            )
            endpoint = self.client.online_endpoints.get(endpoint_name)

            traffic_percentage = 0
            if endpoint.traffic:
                traffic_percentage = endpoint.traffic.get(deployment_name, 0)

            return {
                "deployment_name": deployment_name,
                "endpoint_name": endpoint_name,
                "status": deployment_status.get("provisioning_state"),
                "ready_replicas": deployment_status.get("ready_replica_count", 0),
                "total_replicas": deployment_status.get("instance_count", 0),
                "endpoint_url": self.safe_getattr(endpoint, "scoring_uri"),
                "traffic_percentage": traffic_percentage,
                "last_updated": __import__("time").time(),
                # Placeholder for future metrics integration
                "requests_per_minute": None,
                "average_latency_ms": None,
                "error_rate_percent": None,
            }
        except Exception as e:
            raise AzureMLClientError(
                f"Failed to get deployment metrics for {deployment_name}: {e}"
            )

    def create_or_get_endpoint_with_metadata(
        self, endpoint_name: str, metadata: Dict[str, Any] = None
    ) -> str:
        """Create endpoint if it doesn't exist, otherwise return existing."""
        try:
            endpoint = self.client.online_endpoints.get(endpoint_name)
            logger.info(f"Using existing endpoint: {endpoint_name}")
            return endpoint_name
        except Exception:
            logger.info(f"Creating new endpoint: {endpoint_name}")

            tags = self.create_tags(
                purpose="automl_model_deployment", **(metadata or {})
            )

            endpoint = ManagedOnlineEndpoint(
                name=endpoint_name,
                description=f"AutoML model endpoint - {endpoint_name}",
                auth_mode="key",
                tags=tags,
            )

            created_endpoint = self.handle_azure_operation(
                f"create_or_get_endpoint_{endpoint_name}",
                self.client.online_endpoints.begin_create_or_update,
                endpoint,
            )

            return created_endpoint.name

    def _get_model_reference(self, model_name: str, model_version: str = None) -> str:
        """Get model reference string."""
        if model_version:
            return f"{model_name}:{model_version}"

        # Get the latest version
        model_list = list(self.client.models.list(name=model_name))
        if not model_list:
            raise AzureMLClientError(f"Model {model_name} not found")

        latest_model = max(model_list, key=lambda x: int(x.version))
        return f"{model_name}:{latest_model.version}"

    def _get_endpoint_deployments(
        self, endpoint_name: str
    ) -> Dict[str, Dict[str, Any]]:
        """Get deployment information for an endpoint."""
        deployments = {}
        try:
            deployment_list = list(
                self.client.online_deployments.list(endpoint_name=endpoint_name)
            )
            for deployment in deployment_list:
                deployments[deployment.name] = {
                    "instance_type": self.safe_getattr(deployment, "instance_type"),
                    "instance_count": self.safe_getattr(deployment, "instance_count"),
                    "model": self.safe_getattr(deployment, "model"),
                    "traffic_percentage": None,  # Will be set from endpoint traffic
                }
        except Exception:
            # If we can't get deployments, continue without them
            pass

        return deployments

    def _endpoint_to_dict(self, endpoint) -> Dict[str, Any]:
        """Convert endpoint to dictionary for schema creation."""
        return {
            "id": self.generate_uuid(),
            "user_id": self.generate_uuid(),  # Will be set by calling route
            "name": endpoint.name,
            "azure_endpoint_name": endpoint.name,
            "azure_endpoint_url": self.safe_getattr(endpoint, "scoring_uri"),
            "auth_mode": endpoint.auth_mode,
            "provisioning_state": endpoint.provisioning_state,
            "tags": endpoint.tags or {},
            "description": endpoint.description,
        }

    def _convert_to_schema(self, endpoint) -> EndpointSchema:
        """Convert Azure ML endpoint to schema format."""
        endpoint_dict = self._endpoint_to_dict(endpoint)
        return EndpointSchema(**endpoint_dict)
