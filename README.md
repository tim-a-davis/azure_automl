# Azure AutoML API

This repository contains a thin REST layer built with **FastAPI** for interacting with Azure Machine Learning's AutoML capabilities. It is intended to sit between a web frontend and Azure, providing a unified set of HTTP endpoints to manage datasets, run experiments and deploy models.

The application exposes several routes that wrap the Azure ML SDK. Incoming requests are authenticated via a simple JWT bearer token and tenant information is attached to the request. Azure credentials and database connection details are loaded from environment variables. Metadata for datasets, runs and models is stored in an Azure SQL Database through SQLAlchemy.

## Features

- Upload datasets to the workspace
- Launch AutoML experiments and monitor runs
- Browse registered models and endpoints
- Example background tasks for log streaming and dataset profiling

The service stores metadata in an Azure SQL Database using SQLAlchemy. Connection details and Azure credentials are supplied via environment variables or a `.env` file read by `Settings` in `automlapi.config`.

## Dependencies

To run the API you will need access to several Azure resources and some local tools:

- **Python 3.11** along with [uv](https://github.com/astral-sh/uv) for installing packages.
- An **Azure subscription** containing an Azure Machine Learning workspace.
- A **service principal** with permissions to the workspace (`AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`).
- An **Azure SQL Database** for persisting metadata (`SQL_SERVER`, `SQL_DATABASE` and optional `SQL_USERNAME`/`SQL_PASSWORD`).
- A secret used to sign JSON Web Tokens (`JWT_SECRET`).
- [fastapi-mcp](https://pypi.org/project/fastapi-mcp/) to expose the API as an MCP server.

## Quick start

1. Install dependencies using [uv](https://github.com/astral-sh/uv):

   ```bash
   uv sync
   ```

2. Provide the required Azure and database settings as environment variables. At a minimum the following values are expected:

   - `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`
   - `AZURE_SUBSCRIPTION_ID`, `AZURE_ML_WORKSPACE`, `AZURE_ML_RESOURCE_GROUP`
   - `JWT_SECRET`

3. Initialize the database tables:

   ```bash
   uv run python scripts/create_tables.py
   ```

4. Launch the API server:

   ```bash
   uv run python -m automlapi.runserver
   ```

   The server listens on `http://0.0.0.0:8000`.

## Endpoints

The following routes are implemented by `automlapi.routes`:

- `POST /datasets` – upload a file and register it as an Azure ML dataset.
- `GET  /datasets` – list available datasets.
- `POST /experiments` – start an experiment using the provided configuration.
- `GET  /experiments` – list experiments in the workspace.
- `GET  /runs` – list runs for the workspace.
- `GET  /models` – list registered models.
- `GET  /endpoints` – list deployment endpoints.
- `POST /users` – create a user record.
- `GET  /users` – list users.

WebSocket endpoints are available for run status and endpoint traffic streaming. See the source under `src/automlapi/routes` for details.

## Using as an MCP server

The API can be exposed as a [Model Context Protocol](https://tadata.com) (MCP) server by leveraging the [fastapi-mcp](https://pypi.org/project/fastapi-mcp/) library. When the application starts it mounts an MCP server at the `/mcp` path, automatically converting available routes into MCP tools that language models can invoke.

With the package installed, no additional configuration is required. Simply start the server and query the MCP endpoint:

```bash
uv run python -m automlapi.runserver
# tools will be available under http://localhost:8000/mcp
```

Consult the [fastapi-mcp documentation](https://fastapi-mcp.tadata.com/) for advanced usage and authentication options.

## Setting up Azure RBAC passthrough

The route under `/rbac/assignments` lists role assignments by exchanging the caller's
Azure AD token for a token targeted at the Azure Management API. To enable this
flow you need to configure an app registration and grant the appropriate
permissions:

1. **Create an app registration** for the FastAPI service in Microsoft Entra ID
   and mark it as a *web* application. Note the client ID and tenant ID and add a
   client secret.
2. Under **Expose an API** add an Application ID URI, e.g. `api://<client-id>`,
   and publish a scope named `access_as_user`.
3. Under **API permissions** add *Azure Service Management* → `user_impersonation`
   (delegated) and grant admin consent so the app can perform the on-behalf-of
   exchange.
4. Assign the required RBAC roles (for example `User Access Administrator`) to
   the app registration at the subscription or resource group level so that ARM
   calls can succeed.
5. Provide the `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET` and
   `AZURE_SUBSCRIPTION_ID` environment variables when running the API.

Once configured, clients obtain an access token for `api://<client-id>` and call
the `/rbac/assignments` endpoint with `Authorization: Bearer <token>`. The API
validates the token, exchanges it for an ARM token and lists role assignments for
the configured subscription.

## Testing

Run unit tests with `uv run pytest`:

```bash
uv run pytest
```

## Project status

This implementation acts as a starting point. A number of areas require further work (see `future_work.md`) before it can serve as a full production API.
