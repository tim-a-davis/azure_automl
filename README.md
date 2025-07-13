# Azure AutoML API

A REST API built with **FastAPI** for interacting with Azure Machine Learning's AutoML capabilities. This service provides unified HTTP endpoints to manage datasets, run experiments, and deploy models.

## Features

- **Dataset Management**: Upload and manage ML datasets
- **AutoML Experiments**: Launch and monitor automated ML experiments
- **Model Management**: Browse registered models and deployment endpoints
- **Azure AD Integration**: Production-ready authentication with token exchange
- **MCP Server**: Expose API as Model Context Protocol server for AI agents
- **Background Tasks**: Async processing for long-running operations

## Quick Start

1. **Install dependencies**:
   ```bash
   uv sync
   ```

2. **Set up environment** (create `.env` file):
   ```env
   JWT_SECRET=your-secret-key
   AZURE_TENANT_ID=your-tenant-id
   AZURE_CLIENT_ID=your-client-id
   AZURE_CLIENT_SECRET=your-client-secret
   AZURE_SUBSCRIPTION_ID=your-subscription-id
   AZURE_ML_WORKSPACE=your-workspace-name
   AZURE_ML_RESOURCE_GROUP=your-resource-group
   ```

3. **Initialize database**:
   ```bash
   uv run python scripts/create_tables.py
   ```

4. **Start the server**:
   ```bash
   uv run python -m automlapi.runserver
   ```

   Server runs at `http://localhost:8005`

## Quick Testing

Generate a test token and try the API:

```bash
# Generate test token
uv run python scripts/create_token.py testuser dev-tenant 24

# Test endpoints
TOKEN="your-generated-token"
curl -H "Authorization: Bearer $TOKEN" http://localhost:8005/auth/me
curl -H "Authorization: Bearer $TOKEN" http://localhost:8005/datasets
```

## API Endpoints

### Core Endpoints
- `POST /auth/exchange` – Exchange Azure AD token for API token
- `GET /auth/me` – Get current user info
- `GET|POST /datasets` – Manage datasets
- `GET|POST /experiments` – Manage AutoML experiments
- `GET /runs` – List experiment runs
- `GET /models` – List registered models
- `GET|POST /endpoints` – Manage deployment endpoints

### Documentation
- Swagger UI: `http://localhost:8005/docs`
- ReDoc: `http://localhost:8005/redoc`
- OpenAPI JSON: `http://localhost:8005/openapi.json`

## Documentation

For detailed setup and usage instructions, see the documentation in the `/docs` folder:

- **[Installation Guide](docs/installation.md)** - Dependencies, prerequisites, and setup
- **[Authentication Guide](docs/authentication.md)** - Azure AD integration and security
- **[Database Setup](docs/database-setup.md)** - Azure SQL Database configuration
- **[API Reference](docs/api-reference.md)** - Complete endpoint documentation
- **[Testing Guide](docs/testing.md)** - Testing approaches and examples
- **[Deployment Guide](docs/deployment.md)** - Production deployment and MCP server
- **[RBAC Guide](docs/RBAC.md)** - Role-based access control system

## Development vs Production

The API supports two modes:

- **Local Development**: Uses SQLite (`ENVIRONMENT=local`)
- **Production**: Uses Azure SQL Database (`ENVIRONMENT=production`)

## Testing

Run the test suite:

```bash
uv run pytest
```

For comprehensive testing approaches including custom tokens, Postman, and automated testing, see the [Testing Guide](docs/testing.md).

## Architecture

```
Frontend (React/Vue/etc)
    ↓ (Azure AD authentication)
Azure AutoML API (FastAPI)
    ↓ (Service Principal auth)
Azure ML Workspace
    ↓ (Metadata storage)
Azure SQL Database
```

The API acts as a secure middleware layer between your frontend applications and Azure ML services, handling authentication, data management, and experiment orchestration.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
