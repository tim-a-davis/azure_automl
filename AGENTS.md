# AGENTS.md

## Azure AutoML API Agent Guide

This document provides essential information for AI agents working with the Azure AutoML API project.

## Project Overview

This is a FastAPI-based REST API that provides a thin layer between web frontends and Azure Machine Learning's AutoML capabilities. The API handles dataset management, experiment execution, model deployment, and provides authentication through JWT tokens with Azure AD integration.

## Package Management

This project uses **uv** for Python package management. Use the following commands:

```bash
# Install dependencies
uv sync

# Run Python scripts
uv run python <script_name>

# Run the API server
uv run python -m automlapi.runserver

# Create database tables
uv run python scripts/create_tables.py

# Generate development JWT tokens
uv run python scripts/create_token.py <user_id> <tenant_id> <hours>
```

## Authentication Flow

The API supports two authentication modes:

### Production Mode: Azure AD Integration

The production authentication flow involves:

1. **Token Exchange**: Exchange an Azure AD token for an API token via `POST /auth/exchange`
2. **API Access**: Use the returned JWT token in the `Authorization: Bearer <token>` header

**Token validation process:**
- Azure AD token is validated using JWKS (JSON Web Key Set) from Microsoft
- Required scope: `access_as_user` 
- Audience must match: `api://{azure_client_id}`
- Issuer must be: `https://login.microsoftonline.com/{tenant_id}/v2.0`
- Upon validation, a custom JWT token is issued with 1-hour expiration

### Development Mode: Custom JWT Tokens

For testing and development, generate tokens directly:

```bash
uv run python scripts/create_token.py user123 my-tenant 24
```

This creates a 24-hour valid token that bypasses Azure AD validation.

## Required Environment Variables

### Azure Configuration
- `AZURE_TENANT_ID` - Azure AD tenant ID
- `AZURE_CLIENT_ID` - Service principal client ID  
- `AZURE_CLIENT_SECRET` - Service principal secret
- `AZURE_SUBSCRIPTION_ID` - Azure subscription ID
- `AZURE_ML_WORKSPACE` - Azure ML workspace name
- `AZURE_ML_RESOURCE_GROUP` - Resource group name

### Database Configuration
- `SQL_SERVER` - Azure SQL Server hostname (default: automldbserver.database.windows.net)
- `SQL_DATABASE` - Database name (default: automl)

### Security
- `JWT_SECRET` - Secret key for signing JWT tokens

### Environment Mode
- `ENVIRONMENT` - Set to "local" for SQLite, "production" for Azure SQL

## Database Architecture

- **Production**: Azure SQL Database with Azure AD Service Principal authentication
- **Development**: SQLite database (`automl_local.db`)
- **ORM**: SQLAlchemy with Alembic migrations
- **Models**: Users, Datasets, Experiments, Runs, Models, Endpoints with proper foreign key relationships

## API Endpoints

### Authentication
- `POST /auth/exchange` - Exchange Azure AD token for API token
- `GET /auth/me` - Get current user information

### Core Resources
- `POST|GET /datasets` - Dataset management
- `POST|GET /experiments` - Experiment configuration and listing
- `GET /runs` - Training run status and results
- `GET /models` - Registered model information
- `GET /endpoints` - Deployment endpoint management

### Administration
- `POST|GET /users` - User management
- `GET /rbac/assignments` - Azure role assignments

## MCP Server Integration

The API can function as a Model Context Protocol (MCP) server via the `fastapi-mcp` library:

- MCP endpoint available at `/mcp`
- All HTTP routes automatically converted to MCP tools
- Authentication integrated with MCP auth flow
- Language models can invoke API functionality directly

## Development Quick Start

1. Install dependencies: `uv sync`
2. Set environment variables (or create `.env` file)
3. Initialize database: `uv run python scripts/create_tables.py`
4. Start server: `uv run python -m automlapi.runserver`
5. Server runs on `http://0.0.0.0:8005`

## Project Structure

```
src/automlapi/
├── auth.py              # JWT validation utilities
├── config.py            # Settings and environment configuration  
├── main.py              # FastAPI app setup and middleware
├── runserver.py         # Server entry point
├── db/
│   └── models.py        # SQLAlchemy database models
├── routes/              # API endpoint implementations
├── schemas/             # Pydantic request/response models
├── services/            # Azure ML integration logic
└── tasks/               # Background job definitions
```
