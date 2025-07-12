"""FastAPI application setup and entry point."""

from contextlib import asynccontextmanager

import uvicorn
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi_mcp.server import FastApiMCP
from fastapi_mcp.types import AuthConfig

from .auth import get_current_user
from .config import settings
from .routes import auth, datasets, endpoints, experiments, models, rbac, runs, users

scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    from .tasks.background import collect_endpoint_metrics

    scheduler.add_job(collect_endpoint_metrics, "interval", minutes=5)
    scheduler.start()
    try:
        yield
    finally:
        scheduler.shutdown()


app = FastAPI(lifespan=lifespan)


# Add exception handlers first
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Return a generic 500 response for unhandled exceptions."""
    return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Return validation errors in a standard format."""
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_tenant(request: Request, call_next):
    """Extract tenant ID from JWT token and attach it to the request state."""
    token = request.headers.get("authorization", "").replace("Bearer ", "")
    request.state.tenant_id = None
    if token:
        try:
            import jwt

            payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
            request.state.tenant_id = payload.get("tid")
        except Exception:
            pass
    response = await call_next(request)
    return response


# Include all routers
app.include_router(auth.router)
app.include_router(datasets.router)
app.include_router(experiments.router)
app.include_router(runs.router)
app.include_router(models.router)
app.include_router(endpoints.router)
app.include_router(users.router)
app.include_router(rbac.router)

# Setup MCP after all routes are added
mcp = FastApiMCP(
    app,
    describe_all_responses=True,
    describe_full_response_schema=True,
    auth_config=AuthConfig(
        dependencies=[Depends(get_current_user)],
        issuer="http://localhost:8005",  # Our app's base URL
        audience="automl-api",
        default_scope="openid profile email automl:read automl:write",
    ),
)
mcp.mount()
mcp.setup_server()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
