from unittest.mock import patch
import datetime
from app.services.automl import AzureAutoMLService

@patch("app.services.automl.MLClient")
@patch("app.services.automl.ClientSecretCredential")
def test_list_datasets(mock_cred, mock_client):
    mock_client.return_value.data.list.return_value = [
        {"id": "11111111-1111-1111-1111-111111111111", "tenant_id": "t"}
    ]
    svc = AzureAutoMLService()
    datasets = svc.list_datasets()
    assert len(datasets) == 1


@patch("app.services.automl.ClientSecretCredential")
@patch("app.services.automl.MLClient")
@patch("app.services.automl.automl.classification")
def test_start_experiment(mock_classification, mock_client, mock_cred):
    mock_job = object()
    mock_classification.return_value = mock_job
    mock_client.return_value.jobs.create_or_update.return_value = type(
        "Job",
        (),
        {
            "id": "11111111-1111-1111-1111-111111111111",
            "name": "job1",
            "creation_context": type("ctx", (), {"created_at": datetime.datetime.now()})(),
        },
    )()
    svc = AzureAutoMLService()
    from app.schemas.experiment import Experiment
    exp = Experiment(
        id="11111111-1111-1111-1111-111111111111",
        tenant_id="t",
        task_type="classification",
        training_data="/data",
        target_column_name="y",
        compute="cpu",
    )
    run = svc.start_experiment(exp)
    assert run.job_name == "job1"
