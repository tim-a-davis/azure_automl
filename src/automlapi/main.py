from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import uvicorn

from .routes import datasets, experiments, runs, models, endpoints, users, rbac
from .config import settings

app = FastAPI()


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"detail": exc.errors()})

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_tenant(request: Request, call_next):
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

app.include_router(datasets.router)
app.include_router(experiments.router)
app.include_router(runs.router)
app.include_router(models.router)
app.include_router(endpoints.router)
app.include_router(users.router)
app.include_router(rbac.router)

scheduler = AsyncIOScheduler()

@app.on_event("startup")
async def startup_event():
    from .tasks.background import collect_endpoint_metrics

    scheduler.add_job(collect_endpoint_metrics, "interval", minutes=5)
    scheduler.start()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
