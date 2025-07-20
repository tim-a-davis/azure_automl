"""Model management and deployment service for Azure ML."""

import logging
import time
from typing import Any, Dict, List

from azure.ai.ml.entities import Model

from ..schemas.model import Model as ModelSchema
from .azure_client import AzureMLClient, AzureMLClientError

logger = logging.getLogger(__name__)


class ModelService(AzureMLClient):
    """Service for managing models and model registration in Azure ML."""

    def list_models(self) -> List[ModelSchema]:
        """List all models from Azure ML."""
        try:
            models = list(self.client.models.list())
            return [self._convert_to_schema(model) for model in models]
        except Exception as e:
            raise AzureMLClientError(f"Failed to list models: {e}")

    def download_model(self, model_id: str) -> bytes:
        """Download a model package and return its bytes."""
        import os
        import tempfile

        try:
            tmp_dir = tempfile.mkdtemp()
            self.client.models.download(name=model_id, download_path=tmp_dir)

            # Find and return the first file
            for root, _, files in os.walk(tmp_dir):
                for f in files:
                    path = os.path.join(root, f)
                    with open(path, "rb") as fp:
                        return fp.read()

            return b""

        except Exception as e:
            raise AzureMLClientError(f"Failed to download model {model_id}: {e}")

    def register_model_from_job(
        self,
        job_name: str,
        model_name: str,
        parent_metadata: Dict[str, Any],
        best_model_metadata: Dict[str, Any],
    ) -> str:
        """Register a model from a job's outputs using AutoML artifacts."""
        logger.info(f"Registering model from job: {job_name}")

        errors = []

        # Create tags and description
        tags = self.create_model_tags_from_metadata(
            parent_metadata, best_model_metadata
        )
        description = self.format_model_description(
            parent_metadata, best_model_metadata
        )

        # Try MLflow model path first
        try:
            model_path = self.build_model_uri(job_name, "/mlflow-model")
            logger.info(f"Trying MLflow model path: {model_path}")

            model = Model(
                name=model_name,
                path=model_path,
                description=description,
                type="mlflow_model",
                tags=tags,
            )

            registered_model = self.handle_azure_operation(
                f"register_mlflow_model_{model_name}",
                self.client.models.create_or_update,
                model,
            )

            model_reference = f"{registered_model.name}:{registered_model.version}"
            logger.info(f"✅ MLflow model registered successfully: {model_reference}")
            return model_reference

        except Exception as e:
            error_msg = f"MLflow model registration failed: {e}"
            logger.warning(error_msg)
            errors.append(error_msg)

        # Try complete outputs directory as fallback
        try:
            model_path = self.build_model_uri(job_name)
            logger.info(f"Trying complete outputs path: {model_path}")

            tags_with_note = tags.copy()
            tags_with_note["contains_mlflow_model"] = "true"

            model = Model(
                name=model_name,
                path=model_path,
                description=f"{description} - complete outputs with MLflow artifacts",
                type="custom_model",
                tags=tags_with_note,
            )

            registered_model = self.handle_azure_operation(
                f"register_custom_model_{model_name}",
                self.client.models.create_or_update,
                model,
            )

            model_reference = f"{registered_model.name}:{registered_model.version}"
            logger.info(f"✅ Custom model registered successfully: {model_reference}")
            return model_reference

        except Exception as e:
            error_msg = f"Custom model registration failed: {e}"
            logger.error(error_msg)
            errors.append(error_msg)

        # All attempts failed
        error_summary = "; ".join(errors)
        raise AzureMLClientError(
            f"Could not register model from job {job_name}. All registration methods failed: {error_summary}"
        )

    def create_model_tags_from_metadata(
        self, parent_metadata: Dict[str, Any], model_metadata: Dict[str, Any]
    ) -> Dict[str, str]:
        """Create focused tags with the most important metadata fields."""
        base_tags = {
            "deployment_timestamp": str(int(time.time())),
        }

        # Important metadata fields to include as tags
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

        tags = self.create_tags(**base_tags)

        # Add important fields as tags
        for tag_name, value in important_fields:
            if value is not None and len(tags) < 10:  # Azure ML limit
                if isinstance(value, float):
                    tag_value = f"{value:.4f}"
                else:
                    tag_value = str(value)[:256]  # Azure ML tag limit
                tags[tag_name] = tag_value

        return tags

    def format_model_description(
        self, parent_metadata: Dict[str, Any], model_metadata: Dict[str, Any]
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

    def extract_best_model_metadata(
        self, best_job_name: str, best_job_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract detailed metadata from the best performing model job."""
        logger.info(f"Extracting detailed metadata from best job: {best_job_name}")

        try:
            best_job = self.client.jobs.get(best_job_name)

            metadata = {
                "best_job_name": best_job_name,
                "best_score": best_job_info.get("score"),
                "algorithm": best_job_info.get("algorithm", "unknown"),
                "job_status": self.safe_getattr(best_job, "status"),
                "model_explanation_enabled": None,
                "feature_importance_available": None,
            }

            # Extract all metrics from the job info
            if "metrics" in best_job_info:
                for metric_name, metric_value in best_job_info["metrics"].items():
                    metadata[f"metric_{metric_name.lower()}"] = metric_value

            # Extract additional properties from the job
            properties = self.safe_getattr(best_job, "properties", {}) or {}
            for key, value in properties.items():
                if key not in metadata and value is not None:
                    if key.lower() in [
                        "algorithm",
                        "model_explanation",
                        "feature_importance",
                    ]:
                        metadata[key.lower()] = str(value)
                    else:
                        metadata[f"model_property_{key}"] = str(value)

            # Extract outputs information
            outputs = self.safe_getattr(best_job, "outputs")
            if outputs and hasattr(outputs, "keys"):
                metadata["available_outputs"] = ",".join(outputs.keys())

            # Extract job tags
            tags = self.safe_getattr(best_job, "tags", {}) or {}
            for key, value in tags.items():
                if key not in metadata and value is not None:
                    metadata[f"model_tag_{key}"] = str(value)

            logger.info(
                f"Extracted {len([k for k, v in metadata.items() if v is not None])} metadata fields"
            )
            return metadata

        except Exception as e:
            logger.warning(f"Could not extract best model metadata: {e}")
            return {
                "best_job_name": best_job_name,
                "best_score": best_job_info.get("score"),
                "algorithm": best_job_info.get("algorithm", "unknown"),
            }

    def _convert_to_schema(self, model) -> ModelSchema:
        """Convert Azure ML model to schema format."""
        # This would need proper implementation based on ModelSchema
        return ModelSchema(
            id=self.generate_uuid(),
            name=self.safe_getattr(model, "name", "unknown"),
            version=self.safe_getattr(model, "version"),
        )
