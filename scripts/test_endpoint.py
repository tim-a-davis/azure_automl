#!/usr/bin/env python3
"""
Test the deployed AutoML endpoint with sample data.
"""

import json
import os
import sys

import requests

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from azure.ai.ml import MLClient
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


def test_endpoint(endpoint_name: str):
    """Test the deployed endpoint with sample data."""
    client = create_ml_client()

    # Get endpoint details
    endpoint = client.online_endpoints.get(endpoint_name)
    endpoint_url = endpoint.scoring_uri

    print(f"Testing endpoint: {endpoint_name}")
    print(f"Endpoint URL: {endpoint_url}")

    # Get the endpoint key for authentication
    keys = client.online_endpoints.get_keys(endpoint_name)
    primary_key = keys.primary_key

    # Create sample test data based on the feature structure we discovered
    # The model expects 8 features: feature_0 through feature_7
    sample_data = {
        "input_data": {
            "columns": [
                "feature_0",
                "feature_1",
                "feature_2",
                "feature_3",
                "feature_4",
                "feature_5",
                "feature_6",
                "feature_7",
            ],
            "index": [0, 1],
            "data": [
                [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0],  # Sample 1
                [2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0],  # Sample 2
            ],
        }
    }

    # Set up the request
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {primary_key}",
        "azureml-model-deployment": "deployment-10c806e1",  # Specify the deployment
    }

    print("\nSending test request...")
    print(f"Sample data: {json.dumps(sample_data, indent=2)}")

    try:
        response = requests.post(
            endpoint_url, json=sample_data, headers=headers, timeout=30
        )

        print(f"\nResponse Status: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print("✅ Endpoint test successful!")
            print(f"Predictions: {result}")

            # Analyze the prediction results
            if isinstance(result, list) and len(result) > 0:
                print("\nPrediction Analysis:")
                for i, prediction in enumerate(result):
                    print(f"  Sample {i + 1}: {prediction}")
        else:
            print(f"❌ Endpoint test failed: {response.status_code}")
            print(f"Error response: {response.text}")

    except requests.exceptions.Timeout:
        print("❌ Request timed out after 30 seconds")
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_endpoint.py <endpoint_name>")
        print("Example: python test_endpoint.py automl-endpoint-v11")
        sys.exit(1)

    endpoint_name = sys.argv[1]
    test_endpoint(endpoint_name)
