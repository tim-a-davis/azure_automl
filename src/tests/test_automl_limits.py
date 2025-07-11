"""Test the new AutoML limits functionality."""

import uuid

import pytest
from fastapi.testclient import TestClient

from automlapi.main import app
from automlapi.schemas.experiment import Experiment


class TestAutoMLLimits:
    """Test AutoML job limits functionality."""

    @pytest.fixture
    def client(self):
        """Create a test client."""
        return TestClient(app)

    def test_experiment_schema_with_limits(self):
        """Test that Experiment schema accepts limit parameters with defaults."""
        experiment = Experiment(
            id=uuid.uuid4(),
            tenant_id="test-tenant",
            task_type="classification",
            primary_metric="accuracy",
            target_column_name="target",
        )

        # Check that defaults are applied
        assert experiment.max_concurrent_trials == 20
        assert experiment.max_nodes == 10
        assert experiment.max_trials == 300
        assert experiment.trial_timeout_minutes == 15

    def test_experiment_schema_with_custom_limits(self):
        """Test that Experiment schema accepts custom limit parameters."""
        experiment = Experiment(
            id=uuid.uuid4(),
            tenant_id="test-tenant",
            task_type="regression",
            primary_metric="r2_score",
            target_column_name="target",
            enable_early_termination=True,
            exit_score=0.95,
            max_concurrent_trials=50,
            max_cores_per_trial=4,
            max_nodes=20,
            max_trials=500,
            timeout_minutes=120,
            trial_timeout_minutes=30,
        )

        # Check that custom values are set
        assert experiment.enable_early_termination is True
        assert experiment.exit_score == 0.95
        assert experiment.max_concurrent_trials == 50
        assert experiment.max_cores_per_trial == 4
        assert experiment.max_nodes == 20
        assert experiment.max_trials == 500
        assert experiment.timeout_minutes == 120
        assert experiment.trial_timeout_minutes == 30

    def test_experiment_supports_all_task_types(self):
        """Test that experiments support classification, regression, and forecasting."""
        task_types = ["classification", "regression", "forecasting"]

        for task_type in task_types:
            experiment = Experiment(
                id=uuid.uuid4(),
                tenant_id="test-tenant",
                task_type=task_type,
                target_column_name="target",
            )
            assert experiment.task_type == task_type
