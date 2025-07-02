# Future Work

Recent updates added dataset CRUD routes, user management endpoints, timestamp fields and indexes in the database, validation of required settings and a basic CI pipeline. The project is still in an early stage and a number of areas need further work before it can be considered production ready.

## Database

- ~~**Persist metadata** – experiments, runs, models and endpoints should be stored in the database with appropriate foreign keys so that the API can be queried without hitting Azure.~~
- ~~**Migrations** – integrate Alembic for managing schema changes across environments.~~

## API functionality

- ~~**CRUD operations** – implement create/read/update/delete routes for experiments, runs, models and endpoints.~~
- ~~**Comprehensive error handling** – surface Azure SDK failures and validation errors across all routes with helpful responses.~~
- ~~**Background processing** – expand tasks for dataset profiling and run monitoring, persisting results to the database.~~

## Configuration

- **Simplify dependency management** – review remaining dependencies and consider reducing optional packages.

## Testing

- ~~**Expand unit tests** – add coverage for additional routes, database interactions and permission checks.~~

Addressing these items will help turn this codebase into a reliable API layer for Azure AutoML.
