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

## Quick start

1. Install dependencies using [uv](https://github.com/astral-sh/uv):

   ```bash
   uv sync
   ```

2. Provide the required Azure and database settings as environment variables. At a minimum the following values are expected:

   - `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`
   - `AZURE_SUBSCRIPTION_ID`, `AZURE_ML_WORKSPACE`, `AZURE_ML_RESOURCE_GROUP`
   - `JWT_SECRET`

3. Launch the API server:

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

## Testing

Run unit tests with `uv run pytest`:

```bash
uv run pytest
```

## Project status

This implementation acts as a starting point. A number of areas require further work (see `future_work.md`) before it can serve as a full production API.
