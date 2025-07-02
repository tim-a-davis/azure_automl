# Future Work

This project demonstrates how to expose Azure AutoML functionality through a FastAPI service. To make it production ready and fully usable as a middle tier for a web application, a number of areas require further development.

## Database

- **Fix schema bugs** – `AuditEntry` defines the `diff` column twice and lacks indexes or constraints.
- **Add relations** – link datasets, experiments, runs, models and endpoints with proper foreign keys and cascading deletes.
- **Persist metadata** – routes currently interact with Azure directly but rarely store results. Each action should create or update corresponding records in the database so the API can be queried without round‑tripping to Azure.
- **Unique constraints and indexes** – dataset names, model names and endpoint identifiers should be unique per tenant and indexed for performance.
- **Timestamps** – add `created_at`/`updated_at` fields to track changes.
- **User management** – `User` and `Role` tables exist but the API never writes to them. Endpoints for creating users, assigning roles and enforcing permissions are needed.
- **Migrations** – integrate Alembic to manage schema changes across environments.

## API functionality

- **CRUD operations** – only listing endpoints exist for most resources. Implement create/read/update/delete routes for datasets, experiments, runs, models and endpoints.
- **Error handling** – surface Azure SDK failures and validation errors with useful HTTP responses.
- **Background processing** – the `tasks` module contains stubs for log streaming and metric collection. Hook these into the scheduler on startup and persist results.

## Configuration

- **Settings validation** – `automlapi.config` expects many environment variables. Provide defaults where possible and fail fast with clear messages when they are missing.
- **Simplify dependency management** – the project currently relies on `pydantic-settings`, which has version conflicts with Pydantic. Consider pinning compatible versions or replacing it with a lighter approach.

## Testing and CI

- **Expand unit tests** – coverage is limited to a handful of service calls. Add tests for routes, database interactions and error cases.
- **Continuous integration** – automate linting, type checking and tests.

Addressing the above items will help turn this codebase into a robust API layer capable of powering a front‑end web application for Azure AutoML.
