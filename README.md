# Azure AutoML Wrapper

This project exposes a FastAPI service around Azure AutoML for multi-tenant use.

The service persists metadata in an Azure SQL Database. By default it expects a
database named `automl` hosted at `automldb.whatever.microsoft`. The
`SQL_SERVER` and `SQL_DATABASE` settings can be overridden via environment
variables or a `.env` file.

## Delivery Plan

- **Week 1**: configuration, auth, health check, database migrations
- **Week 2**: dataset upload and profiling workflow
- **Week 3**: experiment launch and run monitoring
- **Week 4**: model registration and browsing
- **Week 5**: endpoint deployment and blue-green traffic control
- **Week 6**: cost sync, quota enforcement, credential rotation
- **Week 7**: tests, CI pipeline, deployment documentation
