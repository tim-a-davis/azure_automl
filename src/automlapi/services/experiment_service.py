"""Experiment and job management service for Azure ML."""

from typing import Any, Dict, List
from uuid import uuid4

from azure.ai.ml import Input, automl, command
from azure.ai.ml.constants import AssetTypes
from azure.ai.ml.entities import ResourceConfiguration

from ..schemas.experiment import Experiment as ExperimentSchema
from ..schemas.run import Run as RunSchema
from .azure_client import AzureMLClient, AzureMLClientError


class ExperimentService(AzureMLClient):
    """Service for managing AutoML experiments and jobs."""

    def list_experiments(self) -> List[ExperimentSchema]:
        """List all experiments (jobs) from Azure ML."""
        try:
            jobs = list(self.client.jobs.list())
            return [self._convert_job_to_experiment_schema(job) for job in jobs]
        except Exception as e:
            raise AzureMLClientError(f"Failed to list experiments: {e}")

    def list_runs(self) -> List[RunSchema]:
        """List all runs (jobs) from Azure ML."""
        try:
            jobs = list(self.client.jobs.list())
            return [self._convert_job_to_run_schema(job) for job in jobs]
        except Exception as e:
            raise AzureMLClientError(f"Failed to list runs: {e}")

    def start_experiment(self, config: ExperimentSchema) -> RunSchema:
        """Launch an AutoML job using serverless compute."""
        try:
            # Prepare training data input
            data_input = None
            if config.training_data:
                data_input = Input(type=AssetTypes.MLTABLE, path=config.training_data)

            # Create the appropriate AutoML job based on task type
            job = self._create_automl_job(config, data_input)

            # Submit the job
            submitted = self.handle_azure_operation(
                f"start_experiment_{config.id}", self.client.jobs.create_or_update, job
            )

            # Extract creation context
            ctx = self.safe_getattr(submitted, "creation_context")
            queued_at = self.safe_getattr(ctx, "created_at") if ctx else None

            return RunSchema(
                id=self.generate_uuid(),
                user_id=config.user_id,
                experiment_id=config.id,
                job_name=self.safe_getattr(submitted, "name"),
                queued_at=queued_at,
            )

        except Exception as e:
            raise AzureMLClientError(f"Failed to start experiment: {e}")

    def get_run_metrics(self, run_id: str) -> Dict[str, Any]:
        """Get metrics for a specific run."""
        try:
            run = self.client.jobs.get(run_id)
            return self.safe_getattr(run, "metrics", {})
        except Exception as e:
            raise AzureMLClientError(f"Failed to get run metrics for {run_id}: {e}")

    def stream_run_logs(self, run_id: str):
        """Yield log lines for a running job."""
        try:
            for line in self.client.jobs.stream(run_id):
                yield line
        except Exception as e:
            raise AzureMLClientError(f"Failed to stream logs for {run_id}: {e}")

    def get_child_jobs_with_scores(self, experiment_name: str) -> List[Dict[str, Any]]:
        """Get all child jobs and their scores from an AutoML experiment."""
        try:
            child_jobs = list(self.client.jobs.list(parent_job_name=experiment_name))
            jobs_with_scores = []

            for job in child_jobs:
                job_info = self._extract_job_performance_info(job)
                if job_info.get("score") is not None:
                    jobs_with_scores.append(job_info)

            # Sort by score (highest first)
            jobs_with_scores.sort(key=lambda x: x.get("score", 0), reverse=True)
            return jobs_with_scores

        except Exception as e:
            raise AzureMLClientError(
                f"Failed to get child jobs for {experiment_name}: {e}"
            )

    def extract_parent_job_metadata(self, parent_job_name: str) -> Dict[str, Any]:
        """Extract metadata from the parent AutoML job."""
        try:
            parent_job = self.client.jobs.get(parent_job_name)

            metadata = {
                "experiment_name": parent_job_name,
                "task_type": None,
                "primary_metric": None,
                "dataset_name": None,
                "target_column": None,
                "training_data_path": None,
                "compute_target": None,
                "job_status": self.safe_getattr(parent_job, "status"),
            }

            # Extract task information
            task = self.safe_getattr(parent_job, "task")
            if task:
                metadata["task_type"] = self.safe_getattr(task, "type")
                metadata["primary_metric"] = self.safe_getattr(task, "primary_metric")
                metadata["target_column"] = self.safe_getattr(
                    task, "target_column_name"
                )

                # Extract training data info
                training_data = self.safe_getattr(task, "training_data")
                if training_data:
                    metadata["training_data_path"] = self.safe_getattr(
                        training_data, "path"
                    )
                    metadata["dataset_name"] = self.safe_getattr(training_data, "name")

            # Extract limits and other configuration
            limits = self.safe_getattr(parent_job, "limits")
            if limits:
                metadata.update(
                    {
                        "max_trials": self.safe_getattr(limits, "max_trials"),
                        "timeout_minutes": self.safe_getattr(limits, "timeout_minutes"),
                        "enable_early_termination": self.safe_getattr(
                            limits, "enable_early_termination"
                        ),
                    }
                )

            # Extract compute target
            metadata["compute_target"] = self.safe_getattr(parent_job, "compute")

            return metadata

        except Exception as e:
            return {
                "experiment_name": parent_job_name,
                "task_type": "unknown",
                "error": str(e),
            }

    def _create_automl_job(self, config: ExperimentSchema, data_input):
        """Create appropriate AutoML job based on task type."""
        common_params = {
            "experiment_name": "automl-experiment",
            "training_data": data_input,
            "target_column_name": config.target_column_name,
            "n_cross_validations": config.n_cross_validations or 5,
        }

        # Add serverless compute configuration
        resource_config = ResourceConfiguration(
            instance_type="Standard_DS3_v2",
            instance_count=1,
        )

        if config.task_type == "classification":
            job = automl.classification(
                **common_params,
                primary_metric=config.primary_metric or "accuracy",
            )
        elif config.task_type == "regression":
            job = automl.regression(
                **common_params,
                primary_metric=config.primary_metric or "r2_score",
            )
        elif config.task_type == "forecasting":
            job = automl.forecasting(
                **common_params,
                primary_metric=config.primary_metric
                or "normalized_root_mean_squared_error",
            )
        else:
            # Fallback to command job
            job = command(
                name=f"job-{uuid4()}",
                command="echo experiment",
                environment="azureml:AzureML-sklearn-1.0-ubuntu20.04-py38-cpu@latest",
            )

        # Configure job limits and resources
        self._configure_job_limits(job, config)
        if hasattr(job, "resources"):
            job.resources = resource_config

        return job

    def _configure_job_limits(self, job, config: ExperimentSchema):
        """Configure limits for AutoML jobs."""
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

    def _extract_job_performance_info(self, job) -> Dict[str, Any]:
        """Extract performance information from a job."""
        job_info = {
            "name": self.safe_getattr(job, "name"),
            "status": self.safe_getattr(job, "status"),
            "algorithm": "unknown",
            "score": None,
            "metrics": {},
            "job_type": self.safe_getattr(job, "type"),
        }

        # Extract properties and scores
        properties = self.safe_getattr(job, "properties", {}) or {}
        for key, value in properties.items():
            key_lower = key.lower()

            # Look for primary score
            if key_lower in ["score", "accuracy", "primary_metric_score"]:
                try:
                    job_info["score"] = float(value)
                except (ValueError, TypeError):
                    pass

            # Look for algorithm
            if key_lower in ["algorithm", "model_name", "estimator"]:
                job_info["algorithm"] = str(value)

            # Store other metrics
            if any(
                metric in key_lower
                for metric in ["accuracy", "precision", "recall", "f1", "auc"]
            ):
                try:
                    job_info["metrics"][key] = float(value)
                    if job_info["score"] is None and key_lower in [
                        "accuracy",
                        "auc",
                        "roc_auc",
                    ]:
                        job_info["score"] = float(value)
                except (ValueError, TypeError):
                    pass

        return job_info

    def _convert_job_to_experiment_schema(self, job) -> ExperimentSchema:
        """Convert Azure ML job to experiment schema."""
        # This would need proper implementation based on ExperimentSchema
        return ExperimentSchema(
            id=self.generate_uuid(),
            task_type=self.safe_getattr(job, "task_type", "unknown"),
        )

    def _convert_job_to_run_schema(self, job) -> RunSchema:
        """Convert Azure ML job to run schema."""
        # This would need proper implementation based on RunSchema
        return RunSchema(
            id=self.generate_uuid(),
            job_name=self.safe_getattr(job, "name"),
        )
