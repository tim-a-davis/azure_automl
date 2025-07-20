"""Dataset management service for Azure ML."""

import os
import tempfile
from typing import Any, Dict, List

from azure.ai.ml.constants import AssetTypes
from azure.ai.ml.entities import Data

from ..schemas.dataset import Dataset as DatasetSchema
from .azure_client import AzureMLClient, AzureMLClientError


class DatasetService(AzureMLClient):
    """Service for managing datasets in Azure ML."""

    def list_datasets(self) -> List[DatasetSchema]:
        """List all datasets from Azure ML."""
        try:
            datasets = list(self.client.data.list())
            return [self._convert_to_schema(dataset) for dataset in datasets]
        except Exception as e:
            raise AzureMLClientError(f"Failed to list datasets: {e}")

    def upload_dataset(self, dataset_name: str, data: bytes) -> Dict[str, Any]:
        """Upload a dataset to Azure ML as MLTable format for AutoML compatibility."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Create the dataset CSV file
            csv_file_path = os.path.join(tmp_dir, "dataset.csv")
            with open(csv_file_path, "wb") as f:
                f.write(data)

            # Create MLTable YAML file for AutoML compatibility
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

            # Create and upload the dataset
            dataset = Data(
                name=dataset_name,
                path=tmp_dir,
                type=AssetTypes.MLTABLE,
                description=f"MLTable dataset for {dataset_name} - AutoML compatible",
            )

            created = self.handle_azure_operation(
                f"upload_dataset_{dataset_name}",
                self.client.data.create_or_update,
                dataset,
            )

            info = self.safe_getattr(created, "_to_dict", lambda: {})()

        return {
            "id": self.generate_uuid(),
            "name": info.get("name", dataset_name),
            "version": info.get("version"),
            "storage_uri": info.get("path", tmp_dir),
        }

    def _convert_to_schema(self, dataset) -> DatasetSchema:
        """Convert Azure ML dataset to schema format."""
        # This would need to be implemented based on the actual DatasetSchema
        # For now, return a placeholder
        return DatasetSchema(
            id=self.generate_uuid(),
            name=self.safe_getattr(dataset, "name", "unknown"),
            version=self.safe_getattr(dataset, "version"),
        )
