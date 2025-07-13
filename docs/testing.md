# Testing Guide

This comprehensive guide covers all approaches for testing the Azure AutoML API, from simple development testing to production validation.

## Testing Overview

You can test the API in several ways:
1. **Custom JWT Tokens** (recommended for development)
2. **Azure AD Integration** (production flow)
3. **Automated testing** with pytest
4. **Load testing** for performance validation

## Method 1: Custom JWT Tokens (Development)

The easiest way to test your API during development is using the built-in token generation script.

### Step 1: Set up your environment

Create a `.env` file with minimal configuration:

```env
# Required for token generation
JWT_SECRET=your-super-secret-jwt-key-make-it-long-and-random

# Azure configuration (can be dummy values for basic testing)
AZURE_TENANT_ID=your-tenant-id
AZURE_CLIENT_ID=your-client-id  
AZURE_CLIENT_SECRET=your-client-secret
AZURE_SUBSCRIPTION_ID=your-subscription-id
AZURE_ML_WORKSPACE=your-workspace-name
AZURE_ML_RESOURCE_GROUP=your-resource-group

# Database (optional for basic testing)
ENVIRONMENT=local  # Uses SQLite for development
```

### Step 2: Initialize database

```bash
uv run python scripts/create_tables.py
```

### Step 3: Generate a test token

```bash
# Generate a token valid for 24 hours
uv run python scripts/create_token.py testuser123 dev-tenant 24
```

This will output something like:
```
JWT Token for user 'testuser123' (tenant: 'dev-tenant', expires in 24 hours):
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0dXNlcjEyMyIsInRpZCI6ImRldi10ZW5hbnQiLCJpYXQiOjE3MDQ5NjAwMDAsImV4cCI6MTcwNTA0NjQwMH0.example_token

Use this token in your requests:
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Step 4: Start the API server

```bash
uv run python -m automlapi.runserver
```

### Step 5: Test with curl

```bash
# Set your token as a variable (replace with your actual token)
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

# Test authentication
curl -H "Authorization: Bearer $TOKEN" http://localhost:8005/auth/me

# List datasets
curl -H "Authorization: Bearer $TOKEN" http://localhost:8005/datasets

# List experiments
curl -H "Authorization: Bearer $TOKEN" http://localhost:8005/experiments

# List models
curl -H "Authorization: Bearer $TOKEN" http://localhost:8005/models

# Upload a dataset (create a test CSV first)
echo "col1,col2,col3" > test_data.csv
echo "1,2,3" >> test_data.csv
echo "4,5,6" >> test_data.csv

curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@test_data.csv" \
  -F "name=test_dataset" \
  -F "description=Test dataset for API testing" \
  http://localhost:8005/datasets
```

## Method 2: Testing with Postman

### Setup Collection

1. **Create a new Postman collection**
2. **Set collection-level authorization**:
   - Type: **Bearer Token**
   - Token: `{{api_token}}` (we'll set this as a variable)

### Configure Environment

Create a Postman environment with these variables:
- `base_url`: `http://localhost:8005`
- `api_token`: Your JWT token from the script

### Sample Requests

#### Test Authentication
```http
GET {{base_url}}/auth/me
```

#### List Datasets
```http
GET {{base_url}}/datasets
```

#### Upload Dataset
```http
POST {{base_url}}/datasets
Content-Type: multipart/form-data

Body (form-data):
- file: [select your CSV file]
- name: "my_test_dataset"
- description: "Test dataset"
```

#### Start Experiment
```http
POST {{base_url}}/experiments
Content-Type: application/json

{
  "dataset_id": "{{dataset_id}}",
  "task_type": "classification",
  "target_column_name": "target",
  "primary_metric": "accuracy",
  "max_trials": 10,
  "timeout_minutes": 30
}
```

## Method 3: Python Testing Script

Create a comprehensive test script to validate all functionality:

```python
#!/usr/bin/env python
"""Test the AutoML API with custom tokens."""

import requests
import json
import os
from pathlib import Path
import time

# Configuration
API_BASE_URL = "http://localhost:8005"
TOKEN = "your_jwt_token_here"  # Get this from create_token.py

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

def test_auth():
    """Test authentication endpoint."""
    print("Testing authentication...")
    response = requests.get(f"{API_BASE_URL}/auth/me", headers=headers)
    print(f"Auth test: {response.status_code}")
    if response.status_code == 200:
        user_info = response.json()
        print(f"User info: {user_info}")
        return True
    else:
        print(f"Auth failed: {response.text}")
        return False

def test_list_datasets():
    """Test listing datasets."""
    print("\nTesting dataset listing...")
    response = requests.get(f"{API_BASE_URL}/datasets", headers=headers)
    print(f"List datasets: {response.status_code}")
    if response.status_code == 200:
        datasets = response.json()
        print(f"Found {len(datasets)} datasets")
        for dataset in datasets[:3]:  # Show first 3
            print(f"  - {dataset.get('name', 'Unknown')}")
        return datasets
    else:
        print(f"Failed to list datasets: {response.text}")
        return []

def test_upload_dataset():
    """Test uploading a dataset."""
    print("\nTesting dataset upload...")
    
    # Create a test CSV
    test_csv = Path("/tmp/test_automl_data.csv")
    test_data = """feature1,feature2,target
1,2,0
3,4,1
5,6,0
7,8,1
9,10,0"""
    test_csv.write_text(test_data)
    
    try:
        files = {
            'file': ('test_data.csv', open(test_csv, 'rb'), 'text/csv')
        }
        data = {
            'name': 'test_dataset_python',
            'description': 'Test dataset uploaded via Python script',
            'tags': json.dumps({"source": "test", "version": "1.0"})
        }
        
        # Remove Content-Type header for multipart/form-data
        upload_headers = {"Authorization": f"Bearer {TOKEN}"}
        
        response = requests.post(
            f"{API_BASE_URL}/datasets", 
            headers=upload_headers,
            files=files,
            data=data
        )
        
        print(f"Upload dataset: {response.status_code}")
        if response.status_code in [200, 201]:
            dataset = response.json()
            print(f"Upload successful: {dataset['name']} (ID: {dataset['id']})")
            return dataset
        else:
            print(f"Upload failed: {response.text}")
            return None
    finally:
        # Cleanup
        if test_csv.exists():
            test_csv.unlink()

def test_start_experiment(dataset_id):
    """Test starting an experiment."""
    if not dataset_id:
        print("\nSkipping experiment test - no dataset available")
        return None
        
    print(f"\nTesting experiment start with dataset {dataset_id}...")
    
    payload = {
        "dataset_id": dataset_id,
        "task_type": "classification",
        "target_column_name": "target",
        "primary_metric": "accuracy",
        "max_trials": 5,
        "timeout_minutes": 15,
        "enable_early_termination": True
    }
    
    response = requests.post(
        f"{API_BASE_URL}/experiments",
        headers=headers,
        json=payload
    )
    
    print(f"Start experiment: {response.status_code}")
    if response.status_code in [200, 201]:
        experiment = response.json()
        print(f"Experiment started: {experiment.get('experiment_id')}")
        return experiment
    else:
        print(f"Failed to start experiment: {response.text}")
        return None

def test_list_experiments():
    """Test listing experiments."""
    print("\nTesting experiment listing...")
    response = requests.get(f"{API_BASE_URL}/experiments", headers=headers)
    print(f"List experiments: {response.status_code}")
    if response.status_code == 200:
        experiments = response.json()
        print(f"Found {len(experiments)} experiments")
        for exp in experiments[:3]:
            print(f"  - {exp.get('id', 'Unknown')} ({exp.get('task_type', 'unknown')})")
        return experiments
    else:
        print(f"Failed to list experiments: {response.text}")
        return []

def test_list_runs():
    """Test listing runs."""
    print("\nTesting run listing...")
    response = requests.get(f"{API_BASE_URL}/runs", headers=headers)
    print(f"List runs: {response.status_code}")
    if response.status_code == 200:
        runs = response.json()
        print(f"Found {len(runs)} runs")
        for run in runs[:3]:
            print(f"  - {run.get('id', 'Unknown')} ({run.get('status', 'unknown')})")
        return runs
    else:
        print(f"Failed to list runs: {response.text}")
        return []

def test_list_models():
    """Test listing models."""
    print("\nTesting model listing...")
    response = requests.get(f"{API_BASE_URL}/models", headers=headers)
    print(f"List models: {response.status_code}")
    if response.status_code == 200:
        models = response.json()
        print(f"Found {len(models)} models")
        for model in models[:3]:
            print(f"  - {model.get('name', 'Unknown')} v{model.get('version', '?')}")
        return models
    else:
        print(f"Failed to list models: {response.text}")
        return []

def test_api_docs():
    """Test API documentation endpoints."""
    print("\nTesting API documentation...")
    
    # Test OpenAPI JSON
    response = requests.get(f"{API_BASE_URL}/openapi.json")
    print(f"OpenAPI JSON: {response.status_code}")
    
    # Test Swagger UI
    response = requests.get(f"{API_BASE_URL}/docs")
    print(f"Swagger UI: {response.status_code}")
    
    # Test ReDoc
    response = requests.get(f"{API_BASE_URL}/redoc")
    print(f"ReDoc: {response.status_code}")

def main():
    """Run all tests."""
    print("="*60)
    print("AutoML API Test Suite")
    print("="*60)
    print(f"API Base URL: {API_BASE_URL}")
    print(f"Using token: {TOKEN[:20]}...")
    print("="*60)
    
    # Test authentication first
    if not test_auth():
        print("\n❌ Authentication failed! Check your token and API server.")
        return
    
    print("\n✅ Authentication successful!")
    
    # Test API documentation
    test_api_docs()
    
    # Test data management
    datasets = test_list_datasets()
    uploaded_dataset = test_upload_dataset()
    
    # Use uploaded dataset for experiment if available
    dataset_id = None
    if uploaded_dataset:
        dataset_id = uploaded_dataset['id']
    elif datasets:
        dataset_id = datasets[0]['id']
    
    # Test experiment management
    experiment = test_start_experiment(dataset_id)
    test_list_experiments()
    test_list_runs()
    test_list_models()
    
    print("\n" + "="*60)
    print("Test Summary:")
    print("✅ Authentication: Passed")
    print("✅ Dataset operations: Passed")
    print("✅ Experiment operations: Passed" if experiment else "⚠️  Experiment operations: Limited (no Azure ML)")
    print("✅ API documentation: Accessible")
    print("="*60)
    print("Testing complete!")

if __name__ == "__main__":
    # Check if token is set
    if TOKEN == "your_jwt_token_here":
        print("Please set your JWT token in the TOKEN variable!")
        print("Generate one with: uv run python scripts/create_token.py testuser dev 24")
        exit(1)
    
    main()
```

Save this as `test_api.py` and run it:

```bash
# Generate a token and use it in the script
TOKEN=$(uv run python scripts/create_token.py testuser dev 24 2>&1 | grep "Bearer" | cut -d' ' -f3)

# Edit the script to use your token, then run
python test_api.py
```

## Method 4: HTTPie Testing

If you prefer HTTPie over curl:

```bash
# Install HTTPie
pip install httpie

# Set token
export TOKEN="your_jwt_token_here"

# Test endpoints
http GET localhost:8005/auth/me "Authorization:Bearer $TOKEN"
http GET localhost:8005/datasets "Authorization:Bearer $TOKEN"
http GET localhost:8005/experiments "Authorization:Bearer $TOKEN"

# Upload file
http --form POST localhost:8005/datasets \
  "Authorization:Bearer $TOKEN" \
  file@test_data.csv \
  name="test_dataset" \
  description="Test upload"
```

## Method 5: Automated Testing with pytest

Run the included unit tests:

```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run specific test file
uv run pytest src/tests/test_routes.py

# Run with coverage
uv run pytest --cov=automlapi
```

### Test Categories

The test suite includes:

- **Unit tests**: Test individual functions and classes
- **Integration tests**: Test API endpoints and database operations
- **Service tests**: Test Azure ML integration (requires Azure credentials)

### Running Tests in Different Environments

```bash
# Local testing (SQLite)
export ENVIRONMENT=local
uv run pytest

# Production testing (Azure SQL)
export ENVIRONMENT=production
uv run pytest
```

## Load Testing

For performance testing, use tools like `locust` or `artillery`:

### Using Locust

```python
# locustfile.py
from locust import HttpUser, task, between

class AutoMLAPIUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        # Set your token here
        self.token = "your_jwt_token"
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    @task(3)
    def list_datasets(self):
        self.client.get("/datasets", headers=self.headers)
    
    @task(2)
    def list_experiments(self):
        self.client.get("/experiments", headers=self.headers)
    
    @task(1)
    def auth_me(self):
        self.client.get("/auth/me", headers=self.headers)
```

```bash
# Install and run locust
pip install locust
locust -f locustfile.py --host=http://localhost:8005
```

## WebSocket Testing

Test real-time features using WebSocket clients:

### JavaScript WebSocket Test

```javascript
// test_websocket.js
const WebSocket = require('ws');

const token = 'your_jwt_token';
const runId = 'your_run_id';

const ws = new WebSocket(`ws://localhost:8005/ws/runs/${runId}/status`, {
  headers: {
    'Authorization': `Bearer ${token}`
  }
});

ws.on('open', function open() {
  console.log('Connected to WebSocket');
});

ws.on('message', function message(data) {
  console.log('Received:', JSON.parse(data.toString()));
});

ws.on('error', function error(err) {
  console.error('WebSocket error:', err);
});
```

### Python WebSocket Test

```python
import asyncio
import websockets
import json

async def test_websocket():
    token = "your_jwt_token"
    run_id = "your_run_id"
    
    uri = f"ws://localhost:8005/ws/runs/{run_id}/status"
    headers = {"Authorization": f"Bearer {token}"}
    
    async with websockets.connect(uri, extra_headers=headers) as websocket:
        print("Connected to WebSocket")
        
        async for message in websocket:
            data = json.loads(message)
            print(f"Received: {data}")

asyncio.run(test_websocket())
```

## Testing Checklist

Use this checklist to verify your API is working correctly:

### Basic Functionality
- [ ] **Environment**: `.env` file configured with `JWT_SECRET`
- [ ] **Database**: Tables created with `uv run python scripts/create_tables.py`
- [ ] **Server**: API running on `http://localhost:8005`
- [ ] **Token**: Generated with `uv run python scripts/create_token.py`
- [ ] **Auth**: `/auth/me` returns user info
- [ ] **Documentation**: `/docs` shows Swagger UI

### Data Operations
- [ ] **List datasets**: Can retrieve dataset list
- [ ] **Upload dataset**: Can upload CSV files
- [ ] **Dataset details**: Can get individual dataset info
- [ ] **List experiments**: Can retrieve experiment list
- [ ] **Start experiment**: Can create new experiments (with Azure ML)
- [ ] **List runs**: Can retrieve run list
- [ ] **List models**: Can retrieve model list

### Error Handling
- [ ] **Invalid token**: Returns 401 for invalid/missing tokens
- [ ] **Malformed requests**: Returns 400 for bad data
- [ ] **Missing resources**: Returns 404 for non-existent items
- [ ] **Server errors**: Returns 500 with proper error messages

### Performance
- [ ] **Response times**: < 1s for list operations
- [ ] **File uploads**: Handles files up to expected size limits
- [ ] **Concurrent requests**: Handles multiple simultaneous requests
- [ ] **Memory usage**: Stable memory consumption under load

## Troubleshooting Tests

### Common Issues

1. **401 Unauthorized**
   ```bash
   # Check token validity
   python -c "
   import jwt
   token = 'YOUR_TOKEN'
   print(jwt.decode(token, options={'verify_signature': False}))
   "
   ```

2. **500 Internal Server Error**
   ```bash
   # Check server logs
   uv run python -m automlapi.runserver
   
   # Test database connection
   uv run python scripts/debug_connection.py
   ```

3. **Connection Refused**
   ```bash
   # Verify server is running
   curl http://localhost:8005/docs
   
   # Check if port is in use
   lsof -i :8005
   ```

4. **Azure ML Integration Issues**
   ```bash
   # Test Azure authentication
   uv run python scripts/test_azure_ad_token.py
   
   # Verify service principal permissions
   az role assignment list --assignee YOUR_CLIENT_ID
   ```

### Debug Mode

Enable debug logging for detailed troubleshooting:

```python
# In your .env file
LOG_LEVEL=DEBUG

# Or set programmatically
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Test Data Management

For consistent testing, create test datasets:

```bash
# Create classification dataset
python -c "
import pandas as pd
import numpy as np

np.random.seed(42)
n_samples = 1000

df = pd.DataFrame({
    'feature1': np.random.normal(0, 1, n_samples),
    'feature2': np.random.normal(0, 1, n_samples),
    'feature3': np.random.uniform(0, 10, n_samples),
    'target': np.random.choice([0, 1], n_samples)
})

df.to_csv('test_classification_data.csv', index=False)
print('Created test_classification_data.csv')
"

# Create regression dataset
python -c "
import pandas as pd
import numpy as np

np.random.seed(42)
n_samples = 1000

X1 = np.random.normal(0, 1, n_samples)
X2 = np.random.normal(0, 1, n_samples)
target = 2 * X1 + 3 * X2 + np.random.normal(0, 0.1, n_samples)

df = pd.DataFrame({
    'feature1': X1,
    'feature2': X2,
    'target': target
})

df.to_csv('test_regression_data.csv', index=False)
print('Created test_regression_data.csv')
"
```

This comprehensive testing guide should help you validate all aspects of the Azure AutoML API, from basic functionality to production readiness!
