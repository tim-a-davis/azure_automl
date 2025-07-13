# API Reference

This document provides detailed information about all available API endpoints in the Azure AutoML API.

## Base URL

The API runs on `http://localhost:8005` by default when started with:

```bash
uv run python -m automlapi.runserver
```

## Authentication

All endpoints (except the token exchange endpoint) require authentication using JWT Bearer tokens.

Include the token in the Authorization header:

```
Authorization: Bearer YOUR_JWT_TOKEN
```

See the [Authentication Guide](authentication.md) for details on obtaining tokens.

## Endpoints Overview

The following routes are implemented by `automlapi.routes`:

### Authentication Endpoints

#### Exchange Azure AD Token
- **POST** `/auth/exchange` – Exchange an Azure AD token for an API access token
- **GET** `/auth/me` – Get information about the current user

### Data Management Endpoints

#### Datasets
- **POST** `/datasets` – Upload a file and register it as an Azure ML dataset
- **GET** `/datasets` – List available datasets
- **GET** `/datasets/{id}` – Get details for a specific dataset

#### Experiments
- **POST** `/experiments` – Start an experiment using the provided configuration
- **GET** `/experiments` – List experiments in the workspace
- **GET** `/experiments/{id}` – Get details for a specific experiment

#### Runs
- **GET** `/runs` – List runs for the workspace
- **GET** `/runs/{id}` – Get details for a specific run

#### Models
- **GET** `/models` – List registered models
- **GET** `/models/{id}` – Get details for a specific model

#### Endpoints
- **GET** `/endpoints` – List deployment endpoints
- **POST** `/endpoints` – Create a new deployment endpoint
- **GET** `/endpoints/{id}` – Get details for a specific endpoint

### User Management Endpoints

#### Users
- **POST** `/users` – Create a user record
- **GET** `/users` – List users
- **GET** `/users/{id}` – Get details for a specific user

### RBAC Endpoints

#### Role-Based Access Control
- **GET** `/rbac/assignments` – List Azure role assignments (requires Azure AD token)

## Detailed Endpoint Documentation

### Authentication

#### POST /auth/exchange

Exchange an Azure AD token for an API access token.

**Request Body:**
```json
{
  "azure_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsIng1dCI6..."
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

**Status Codes:**
- `200`: Token exchange successful
- `400`: Invalid Azure token
- `401`: Token validation failed

#### GET /auth/me

Get information about the current authenticated user.

**Headers:**
```
Authorization: Bearer YOUR_JWT_TOKEN
```

**Response:**
```json
{
  "user_id": "user123",
  "tenant_id": "tenant-abc",
  "roles": ["user"],
  "exp": 1704067200
}
```

### Datasets

#### POST /datasets

Upload a file and register it as an Azure ML dataset.

**Headers:**
```
Authorization: Bearer YOUR_JWT_TOKEN
Content-Type: multipart/form-data
```

**Form Data:**
- `file`: The dataset file (CSV, Excel, etc.)
- `name`: Dataset name (string)
- `description`: Dataset description (string, optional)
- `tags`: JSON object with tags (optional)

**Example Request:**
```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@data.csv" \
  -F "name=my_dataset" \
  -F "description=Training data for model" \
  -F "tags={\"environment\": \"production\", \"version\": \"1.0\"}" \
  http://localhost:8005/datasets
```

**Response:**
```json
{
  "id": "uuid-here",
  "name": "my_dataset",
  "description": "Training data for model",
  "storage_uri": "azureml://subscriptions/.../datasets/my_dataset",
  "columns": ["feature1", "feature2", "target"],
  "row_count": 1000,
  "byte_size": 50000,
  "tags": {
    "environment": "production",
    "version": "1.0"
  },
  "uploaded_by": "user123",
  "created_at": "2024-01-01T12:00:00Z"
}
```

#### GET /datasets

List all available datasets.

**Query Parameters:**
- `limit`: Maximum number of datasets to return (default: 100)
- `offset`: Number of datasets to skip (default: 0)
- `uploaded_by`: Filter by uploader user ID

**Example Request:**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8005/datasets?limit=10&offset=0"
```

**Response:**
```json
[
  {
    "id": "uuid-1",
    "name": "dataset1",
    "description": "First dataset",
    "row_count": 1000,
    "byte_size": 50000,
    "uploaded_by": "user123",
    "created_at": "2024-01-01T12:00:00Z"
  },
  {
    "id": "uuid-2",
    "name": "dataset2",
    "description": "Second dataset",
    "row_count": 2000,
    "byte_size": 100000,
    "uploaded_by": "user456",
    "created_at": "2024-01-02T12:00:00Z"
  }
]
```

### Experiments

#### POST /experiments

Start a new AutoML experiment.

**Request Body:**
```json
{
  "dataset_id": "uuid-of-dataset",
  "task_type": "classification",
  "target_column_name": "target",
  "primary_metric": "accuracy",
  "max_trials": 50,
  "timeout_minutes": 60,
  "enable_early_termination": true,
  "n_cross_validations": 5
}
```

**Response:**
```json
{
  "experiment_id": "uuid-experiment",
  "run_id": "uuid-run",
  "status": "queued",
  "job_name": "automl_run_20240101_120000",
  "created_at": "2024-01-01T12:00:00Z"
}
```

**Supported Task Types:**
- `classification`
- `regression`
- `forecasting`

**Supported Primary Metrics:**

**Classification:**
- `accuracy`
- `precision_score_weighted`
- `recall_score_weighted`
- `f1_score_weighted`
- `AUC_weighted`

**Regression:**
- `r2_score`
- `mean_squared_error`
- `mean_absolute_error`
- `root_mean_squared_error`

#### GET /experiments

List all experiments.

**Response:**
```json
[
  {
    "id": "uuid-exp-1",
    "dataset_id": "uuid-dataset-1",
    "task_type": "classification",
    "target_column_name": "target",
    "primary_metric": "accuracy",
    "status": "completed",
    "created_at": "2024-01-01T12:00:00Z"
  }
]
```

### Runs

#### GET /runs

List all experiment runs.

**Query Parameters:**
- `experiment_id`: Filter by experiment ID
- `status`: Filter by run status (`queued`, `running`, `completed`, `failed`)

**Response:**
```json
[
  {
    "id": "uuid-run-1",
    "experiment_id": "uuid-exp-1",
    "job_name": "automl_run_20240101_120000",
    "status": "completed",
    "queued_at": "2024-01-01T12:00:00Z",
    "started_at": "2024-01-01T12:01:00Z",
    "completed_at": "2024-01-01T13:00:00Z",
    "metrics": {
      "accuracy": 0.95,
      "precision": 0.94,
      "recall": 0.96
    },
    "best_model_id": "uuid-model-1"
  }
]
```

### Models

#### GET /models

List all registered models.

**Response:**
```json
[
  {
    "id": "uuid-model-1",
    "name": "automl_model_20240101",
    "version": "1",
    "run_id": "uuid-run-1",
    "algorithm": "LightGBM",
    "metrics": {
      "accuracy": 0.95,
      "precision": 0.94,
      "recall": 0.96
    },
    "created_at": "2024-01-01T13:00:00Z"
  }
]
```

### Endpoints

#### POST /endpoints

Create a new deployment endpoint.

**Request Body:**
```json
{
  "name": "my-endpoint",
  "model_id": "uuid-model-1",
  "compute_type": "aci",
  "cpu_cores": 1,
  "memory_gb": 1,
  "description": "Production endpoint for model"
}
```

**Response:**
```json
{
  "id": "uuid-endpoint-1",
  "name": "my-endpoint",
  "model_id": "uuid-model-1",
  "status": "creating",
  "scoring_uri": null,
  "created_at": "2024-01-01T14:00:00Z"
}
```

#### GET /endpoints

List all deployment endpoints.

**Response:**
```json
[
  {
    "id": "uuid-endpoint-1",
    "name": "my-endpoint",
    "model_id": "uuid-model-1",
    "status": "healthy",
    "scoring_uri": "https://my-endpoint.azureml.net/score",
    "created_at": "2024-01-01T14:00:00Z"
  }
]
```

## WebSocket Endpoints

The API provides WebSocket endpoints for real-time updates:

### Run Status Updates
- **WS** `/ws/runs/{run_id}/status` – Get real-time updates on run status

### Endpoint Traffic
- **WS** `/ws/endpoints/{endpoint_id}/traffic` – Monitor endpoint traffic and performance

**Example WebSocket Usage:**
```javascript
const ws = new WebSocket('ws://localhost:8005/ws/runs/uuid-run-1/status');

ws.onmessage = function(event) {
  const data = JSON.parse(event.data);
  console.log('Run status update:', data);
};
```

## Error Responses

The API uses standard HTTP status codes and returns error details in JSON format:

```json
{
  "error": "validation_error",
  "message": "Invalid request data",
  "details": {
    "field": "target_column_name",
    "issue": "Field is required"
  }
}
```

**Common Status Codes:**
- `200`: Success
- `201`: Created
- `400`: Bad Request (validation error)
- `401`: Unauthorized (invalid or missing token)
- `403`: Forbidden (insufficient permissions)
- `404`: Not Found
- `422`: Unprocessable Entity (invalid data)
- `500`: Internal Server Error

## Rate Limiting

The API implements rate limiting to prevent abuse:

- **Default limit**: 100 requests per minute per user
- **Headers included in response**:
  - `X-RateLimit-Limit`: Request limit per window
  - `X-RateLimit-Remaining`: Requests remaining in current window
  - `X-RateLimit-Reset`: Time when the rate limit resets

## Pagination

List endpoints support pagination:

**Query Parameters:**
- `limit`: Number of items per page (max 1000, default 100)
- `offset`: Number of items to skip

**Response Headers:**
- `X-Total-Count`: Total number of items
- `Link`: Links to first, last, next, and previous pages

## Content Types

**Supported request content types:**
- `application/json` (for JSON data)
- `multipart/form-data` (for file uploads)

**Response content type:**
- `application/json` (all responses)

## API Versioning

The API currently uses URL path versioning:

- Current version: `v1` (default, no prefix required)
- Future versions will use `/v2/`, `/v3/`, etc.

## OpenAPI Documentation

Interactive API documentation is available at:
- Swagger UI: `http://localhost:8005/docs`
- ReDoc: `http://localhost:8005/redoc`
- OpenAPI JSON: `http://localhost:8005/openapi.json`

## SDK and Client Libraries

Example Python client usage:

```python
import requests
import json

class AutoMLClient:
    def __init__(self, base_url, token):
        self.base_url = base_url.rstrip('/')
        self.headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
    
    def list_datasets(self):
        response = requests.get(f'{self.base_url}/datasets', headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def upload_dataset(self, file_path, name, description=None):
        files = {'file': open(file_path, 'rb')}
        data = {'name': name}
        if description:
            data['description'] = description
        
        headers = {'Authorization': self.headers['Authorization']}
        response = requests.post(f'{self.base_url}/datasets', 
                               headers=headers, files=files, data=data)
        response.raise_for_status()
        return response.json()
    
    def start_experiment(self, dataset_id, task_type, target_column, **kwargs):
        payload = {
            'dataset_id': dataset_id,
            'task_type': task_type,
            'target_column_name': target_column,
            **kwargs
        }
        response = requests.post(f'{self.base_url}/experiments', 
                               headers=self.headers, json=payload)
        response.raise_for_status()
        return response.json()

# Usage
client = AutoMLClient('http://localhost:8005', 'your-jwt-token')
datasets = client.list_datasets()
```

## Testing the API

See the [Testing Guide](testing.md) for comprehensive testing approaches, including:
- Using custom JWT tokens for development
- Testing with curl, Postman, and Python scripts
- WebSocket testing
- Load testing considerations
