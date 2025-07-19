#!/usr/bin/env python3
"""
Deploy the best model from a completed AutoML experiment.

This script:
1. Gets all child jobs from an AutoML experiment
2. Finds the job with the highest accuracy score
3. Registers that model
4. Creates an endpoint and deploys the model

Usage: python deploy_best_model.py <experiment_name> <endpoint_name>
"""

import os
import sys
from typing import Dict, List
from uuid import uuid4

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from azure.ai.ml import MLClient
from azure.ai.ml.entities import ManagedOnlineDeployment, ManagedOnlineEndpoint, Model
from azure.identity import ClientSecretCredential

from automlapi.config import settings


def create_ml_client():
    """Create authenticated ML client."""
    cred = ClientSecretCredential(
        tenant_id=settings.azure_tenant_id,
        client_id=settings.azure_client_id,
        client_secret=settings.azure_client_secret,
    )
    return MLClient(
        credential=cred,
        subscription_id=settings.azure_subscription_id,
        resource_group_name=settings.azure_ml_resource_group,
        workspace_name=settings.azure_ml_workspace,
    )


def extract_parent_job_metadata(client: MLClient, parent_job_name: str) -> Dict:
    """Extract metadata from the parent AutoML job."""
    print(f"Extracting metadata from parent job: {parent_job_name}")

    try:
        parent_job = client.jobs.get(parent_job_name)

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
                                if dataset_part and not dataset_part.endswith(".csv"):
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
                metadata["enable_early_termination"] = limits.enable_early_termination

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
    client: MLClient, best_job_name: str, best_job_info: Dict
) -> Dict:
    """Extract detailed metadata from the best performing model job."""
    print(f"Extracting detailed metadata from best job: {best_job_name}")

    try:
        best_job = client.jobs.get(best_job_name)

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


def get_child_jobs_with_scores(client: MLClient, parent_job_name: str) -> List[Dict]:
    """Get all child jobs and their scores from an AutoML experiment."""
    print(f"Getting child jobs for experiment: {parent_job_name}")

    child_jobs = list(client.jobs.list(parent_job_name=parent_job_name))
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

    # Sort by score (highest first for accuracy-based metrics, adjust if needed)
    jobs_with_scores.sort(key=lambda x: x["score"], reverse=True)

    print(f"Found {len(jobs_with_scores)} jobs with scores")

    # Print summary of top jobs
    if jobs_with_scores:
        print("\nTop performing jobs:")
        for i, job in enumerate(jobs_with_scores[:3], 1):
            metrics_summary = []
            if job["metrics"]:
                for k, v in list(job["metrics"].items())[:3]:  # Show first 3 metrics
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


def register_model_from_job(
    client: MLClient,
    job_name: str,
    model_name: str,
    parent_metadata: Dict,
    best_model_metadata: Dict,
) -> str:
    """Register a model from a job's outputs using the complete AutoML artifacts with comprehensive metadata."""
    print(f"Registering model from job: {job_name}")

    # The Azure ML model URI must match this exact regex format:
    subscription_id = settings.azure_subscription_id
    resource_group = settings.azure_ml_resource_group
    workspace_name = settings.azure_ml_workspace

    errors = []

    # Create focused tags with the 10 most important metadata fields
    def create_model_tags():
        tags = {
            "created_by": "deploy_best_model_script",
            "deployment_timestamp": str(int(__import__("time").time())),
        }

        # Top 8 most important tags from experiment and model metadata
        important_fields = [
            ("task_type", parent_metadata.get("task_type")),
            ("primary_metric", parent_metadata.get("primary_metric")),
            ("dataset_name", parent_metadata.get("dataset_name")),
            ("target_column", parent_metadata.get("target_column")),
            ("algorithm", best_model_metadata.get("algorithm")),
            ("best_score", best_model_metadata.get("best_score")),
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

    # Create comprehensive description
    def create_model_description():
        desc_parts = [
            f"AutoML model from experiment '{parent_metadata.get('experiment_name', 'unknown')}'",
        ]

        if parent_metadata.get("task_type"):
            desc_parts.append(f"Task: {parent_metadata['task_type']}")

        if best_model_metadata.get("algorithm"):
            desc_parts.append(f"Algorithm: {best_model_metadata['algorithm']}")

        if best_model_metadata.get("best_score"):
            metric_name = parent_metadata.get("primary_metric", "score")
            desc_parts.append(f"{metric_name}: {best_model_metadata['best_score']:.4f}")

        if parent_metadata.get("dataset_name"):
            desc_parts.append(f"Dataset: {parent_metadata['dataset_name']}")

        if parent_metadata.get("target_column"):
            desc_parts.append(f"Target: {parent_metadata['target_column']}")

        return " | ".join(desc_parts)

    # Try approach 1: Full datastore path with subscription info to MLflow model
    try:
        model_path = f"azureml://subscriptions/{subscription_id}/resourceGroups/{resource_group}/workspaces/{workspace_name}/datastores/workspaceartifactstore/paths/ExperimentRun/dcid.{job_name}/outputs/mlflow-model"

        print(f"Trying full datastore path to MLflow model: {model_path}")

        tags = create_model_tags()
        description = create_model_description()

        model = Model(
            name=model_name,
            path=model_path,
            description=description,
            type="mlflow_model",
            tags=tags,
        )

        registered_model = client.models.create_or_update(model)
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

        tags = create_model_tags()
        tags["contains_mlflow_model"] = "true"
        description = create_model_description()

        model = Model(
            name=model_name,
            path=model_path,
            description=f"{description} - complete outputs with MLflow artifacts",
            type="custom_model",
            tags=tags,
        )

        registered_model = client.models.create_or_update(model)
        model_reference = f"{registered_model.name}:{registered_model.version}"
        print(f"✅ Complete outputs model registered: {model_reference}")
        print(f"📊 Model registered with {len(tags)} metadata tags")
        return model_reference

    except Exception as e:
        print(f"Full outputs path failed: {e}")
        errors.append(f"Full outputs datastore path: {e}")

    # Try approach 3: Upload from downloaded artifacts
    try:
        print("Trying to register from local downloaded artifacts...")

        # We know from our exploration that the artifacts were downloaded to temp_explore_*
        local_mlflow_path = f"./temp_explore_{job_name}/artifacts/outputs/mlflow-model"

        if os.path.exists(local_mlflow_path):
            tags = create_model_tags()
            tags["uploaded_from_local"] = "true"
            description = create_model_description()

            model = Model(
                name=model_name,
                path=local_mlflow_path,  # Local path to MLflow model
                description=f"{description} - uploaded from local artifacts",
                type="mlflow_model",
                tags=tags,
            )

            registered_model = client.models.create_or_update(model)
            model_reference = f"{registered_model.name}:{registered_model.version}"
            print(f"✅ Local MLflow model registered: {model_reference}")
            print(f"📊 Model registered with {len(tags)} metadata tags")
            return model_reference
        else:
            print(f"Local MLflow path does not exist: {local_mlflow_path}")
            errors.append(f"Local MLflow path not found: {local_mlflow_path}")

    except Exception as e:
        print(f"Local MLflow upload failed: {e}")
        errors.append(f"Local MLflow upload: {e}")

    print("All registration attempts failed:")
    for error in errors:
        print(f"  {error}")
    raise Exception(
        f"Could not register model from job {job_name}. All registration methods failed."
    )


def create_or_get_endpoint(client: MLClient, endpoint_name: str) -> str:
    """Create endpoint if it doesn't exist, otherwise return existing."""
    try:
        endpoint = client.online_endpoints.get(endpoint_name)
        print(f"Using existing endpoint: {endpoint_name}")
        return endpoint_name
    except Exception:
        print(f"Creating new endpoint: {endpoint_name}")

        endpoint = ManagedOnlineEndpoint(
            name=endpoint_name,
            description=f"AutoML model endpoint - {endpoint_name}",
            auth_mode="key",
            tags={
                "created_by": "deploy_best_model_script",
                "purpose": "automl_model_deployment",
            },
        )

        created_endpoint = client.online_endpoints.begin_create_or_update(
            endpoint
        ).result()
        print(f"Endpoint created: {created_endpoint.name}")
        return created_endpoint.name


def deploy_model(
    client: MLClient,
    endpoint_name: str,
    model_reference: str,
    deployment_name: str = None,
) -> str:
    """Deploy MLflow model to endpoint using AutoML's complete artifacts."""
    if deployment_name is None:
        deployment_name = f"deployment-{uuid4().hex[:8]}"

    deployment = ManagedOnlineDeployment(
        name=deployment_name,
        endpoint_name=endpoint_name,
        model=model_reference,  # MLflow model with all artifacts
        instance_type="Standard_DS3_v2",
        instance_count=1,
        # No need to specify environment or code_configuration
        # MLflow model format includes everything needed
    )

    try:
        created_deployment = client.online_deployments.begin_create_or_update(
            deployment
        ).result()
        print(f"✅ MLflow deployment created: {created_deployment.name}")

        # Set 100% traffic to this deployment
        print("Setting traffic to 100% for new deployment...")
        endpoint = client.online_endpoints.get(endpoint_name)
        endpoint.traffic = {deployment_name: 100}
        client.online_endpoints.begin_create_or_update(endpoint).result()
        print("✅ Traffic allocation updated")

        return created_deployment.name

    except Exception:
        raise


def main():
    """Main deployment workflow."""
    if len(sys.argv) < 3:
        print("Usage: python deploy_best_model.py <experiment_name> <endpoint_name>")
        print(
            "\nExample: python deploy_best_model.py khaki_pillow_xpkxtr44k4 my-automl-endpoint"
        )
        sys.exit(1)

    experiment_name = sys.argv[1]
    endpoint_name = sys.argv[2]

    try:
        # Initialize client
        client = create_ml_client()

        # Extract parent job metadata first
        parent_metadata = extract_parent_job_metadata(client, experiment_name)

        # Print key parent metadata
        key_fields = [
            "task_type",
            "primary_metric",
            "dataset_name",
            "target_column",
            "compute_target",
        ]
        for field in key_fields:
            value = parent_metadata.get(field)
            if value:
                print(f"  {field.replace('_', ' ').title()}: {value}")

        # Get child jobs with scores
        jobs_with_scores = get_child_jobs_with_scores(client, experiment_name)

        if not jobs_with_scores:
            return

        # Get the best job and extract its metadata
        best_job = jobs_with_scores[0]
        best_model_metadata = extract_best_model_metadata(
            client, best_job["name"], best_job
        )

        # Print best model performance summary

        # Show additional metrics if available
        metric_keys = [k for k in best_model_metadata.keys() if k.startswith("metric_")]
        if metric_keys:
            print("  Additional Metrics:")
            for key in sorted(metric_keys[:5]):  # Show top 5 metrics
                value = best_model_metadata[key]
                metric_name = key.replace("metric_", "").replace("_", " ").title()
                if isinstance(value, (int, float)):
                    print(f"    {metric_name}: {value:.4f}")
                else:
                    print(f"    {metric_name}: {value}")

        # Register the model with comprehensive metadata
        model_name = f"automl-best-{experiment_name.replace('_', '-')}"
        model_reference = register_model_from_job(
            client, best_job["name"], model_name, parent_metadata, best_model_metadata
        )

        # Create or get endpoint
        endpoint_name = create_or_get_endpoint(client, endpoint_name)

        # Deploy the model
        deployment_name = deploy_model(client, endpoint_name, model_reference)

        # Get endpoint URL
        endpoint = client.online_endpoints.get(endpoint_name)
        endpoint_url = getattr(endpoint, "scoring_uri", "Not available")

        # Show metadata summary
        total_parent_fields = len(
            [v for v in parent_metadata.values() if v is not None]
        )
        total_model_fields = len(
            [v for v in best_model_metadata.values() if v is not None]
        )
        print(
            f"📊 Metadata Captured: {total_parent_fields} experiment fields, {total_model_fields} model fields"
        )
        print(f"{'=' * 80}")

    except Exception as e:
        print(f"Deployment failed: {str(e)}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
