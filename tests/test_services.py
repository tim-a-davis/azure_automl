from unittest.mock import MagicMock, patch
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
