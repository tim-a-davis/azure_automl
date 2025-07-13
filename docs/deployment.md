# Deployment Guide

This guide covers production deployment considerations, MCP server configuration, and operational best practices for the Azure AutoML API.

## Model Context Protocol (MCP) Server

The API can be exposed as a [Model Context Protocol](https://tadata.com) (MCP) server by leveraging the [fastapi-mcp](https://pypi.org/project/fastapi-mcp/) library. When the application starts it mounts an MCP server at the `/mcp` path, automatically converting available routes into MCP tools that language models can invoke.

### MCP Server Setup

With the package installed, no additional configuration is required. Simply start the server and query the MCP endpoint:

```bash
uv run python -m automlapi.runserver
# tools will be available under http://localhost:8005/mcp
```

### MCP Configuration

The MCP server automatically exposes API endpoints as tools. You can configure which endpoints are exposed by modifying the MCP settings in `config.py`:

```python
# Enable/disable MCP server
ENABLE_MCP = True

# Configure MCP authentication
MCP_REQUIRE_AUTH = True

# Customize MCP tool names and descriptions
MCP_TOOL_CONFIG = {
    "datasets": {
        "enabled": True,
        "description": "Manage machine learning datasets"
    },
    "experiments": {
        "enabled": True,
        "description": "Run AutoML experiments"
    }
}
```

### Using MCP Tools

Language models can use the MCP tools to interact with the API:

```json
{
  "tool": "mcp_automl_list_datasets",
  "parameters": {}
}
```

Consult the [fastapi-mcp documentation](https://fastapi-mcp.tadata.com/) for advanced usage and authentication options.

## Production Deployment

### Environment Configuration

For production deployments, use environment-specific configuration:

#### Production Environment Variables

```env
# Environment
ENVIRONMENT=production

# Azure AD Configuration
AZURE_TENANT_ID=your-production-tenant-id
AZURE_CLIENT_ID=your-production-client-id
AZURE_CLIENT_SECRET=your-production-client-secret

# Azure ML Configuration
AZURE_SUBSCRIPTION_ID=your-production-subscription-id
AZURE_ML_WORKSPACE=your-production-workspace
AZURE_ML_RESOURCE_GROUP=your-production-resource-group

# Database Configuration
SQL_SERVER=your-production-server.database.windows.net
SQL_DATABASE=your-production-database

# Security
JWT_SECRET=your-production-jwt-secret-from-key-vault
CORS_ORIGINS=https://yourapp.com,https://api.yourapp.com

# Performance
WORKER_COUNT=4
MAX_CONNECTIONS=100
REQUEST_TIMEOUT=300

# Monitoring
LOG_LEVEL=INFO
ENABLE_METRICS=true
HEALTH_CHECK_INTERVAL=30
```

### Container Deployment

#### Dockerfile

```dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    unixodbc-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Microsoft ODBC Driver 18 for SQL Server
RUN curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - \
    && curl https://packages.microsoft.com/config/ubuntu/20.04/prod.list > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y msodbcsql18

# Install uv
RUN pip install uv

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen

# Copy application code
COPY src/ ./src/
COPY scripts/ ./scripts/
COPY alembic/ ./alembic/
COPY alembic.ini ./

# Create non-root user
RUN useradd --create-home --shell /bin/bash automl
RUN chown -R automl:automl /app
USER automl

# Expose port
EXPOSE 8005

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8005/health || exit 1

# Start command
CMD ["uv", "run", "python", "-m", "automlapi.runserver"]
```

#### Docker Compose

```yaml
version: '3.8'

services:
  automl-api:
    build: .
    ports:
      - "8005:8005"
    environment:
      - ENVIRONMENT=production
    env_file:
      - .env.production
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8005/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    volumes:
      - ./logs:/app/logs
    networks:
      - automl-network

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - automl-api
    networks:
      - automl-network

networks:
  automl-network:
    driver: bridge
```

### Kubernetes Deployment

#### Deployment Manifest

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: automl-api
  labels:
    app: automl-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: automl-api
  template:
    metadata:
      labels:
        app: automl-api
    spec:
      containers:
      - name: automl-api
        image: your-registry/automl-api:latest
        ports:
        - containerPort: 8005
        env:
        - name: ENVIRONMENT
          value: "production"
        envFrom:
        - secretRef:
            name: automl-secrets
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8005
          initialDelaySeconds: 30
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /ready
            port: 8005
          initialDelaySeconds: 5
          periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: automl-api-service
spec:
  selector:
    app: automl-api
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8005
  type: LoadBalancer
```

#### ConfigMap and Secrets

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: automl-secrets
type: Opaque
stringData:
  AZURE_TENANT_ID: "your-tenant-id"
  AZURE_CLIENT_ID: "your-client-id"
  AZURE_CLIENT_SECRET: "your-client-secret"
  JWT_SECRET: "your-jwt-secret"
  SQL_SERVER: "your-server.database.windows.net"
  SQL_DATABASE: "your-database"
```

### Azure Container Apps

Deploy using Azure Container Apps for serverless container hosting:

```bash
# Create resource group
az group create --name automl-rg --location eastus

# Create container app environment
az containerapp env create \
  --name automl-env \
  --resource-group automl-rg \
  --location eastus

# Deploy container app
az containerapp create \
  --name automl-api \
  --resource-group automl-rg \
  --environment automl-env \
  --image your-registry/automl-api:latest \
  --target-port 8005 \
  --ingress external \
  --min-replicas 1 \
  --max-replicas 10 \
  --cpu 0.5 \
  --memory 1Gi \
  --env-vars ENVIRONMENT=production \
  --secrets azure-tenant-id=your-tenant-id \
             azure-client-id=your-client-id \
             azure-client-secret=your-client-secret
```

## Security Best Practices

### Authentication & Authorization

1. **Use Azure Key Vault** for sensitive configuration:

```python
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential

def get_secret_from_keyvault(vault_url: str, secret_name: str) -> str:
    credential = DefaultAzureCredential()
    client = SecretClient(vault_url=vault_url, credential=credential)
    secret = client.get_secret(secret_name)
    return secret.value

# In config.py
JWT_SECRET = get_secret_from_keyvault(
    "https://your-keyvault.vault.azure.net/", 
    "jwt-secret"
)
```

2. **Implement certificate-based authentication**:

```python
from azure.identity import CertificateCredential

credential = CertificateCredential(
    tenant_id=AZURE_TENANT_ID,
    client_id=AZURE_CLIENT_ID,
    certificate_path="/path/to/certificate.pem"
)
```

3. **Configure CORS properly**:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourapp.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)
```

### Network Security

1. **Use HTTPS in production**:

```nginx
server {
    listen 443 ssl http2;
    server_name api.yourapp.com;
    
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    
    location / {
        proxy_pass http://automl-api:8005;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

2. **Implement rate limiting**:

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.get("/datasets")
@limiter.limit("10/minute")
async def list_datasets(request: Request):
    # endpoint implementation
    pass
```

3. **Configure firewall rules**:

```bash
# Azure SQL Database firewall
az sql server firewall-rule create \
  --resource-group automl-rg \
  --server your-sql-server \
  --name AllowContainerApps \
  --start-ip-address 10.0.0.0 \
  --end-ip-address 10.255.255.255
```

## Monitoring and Observability

### Application Insights

Configure Azure Application Insights for monitoring:

```python
from opencensus.ext.azure.log_exporter import AzureLogHandler
from opencensus.ext.azure.trace_exporter import AzureExporter
from opencensus.trace.samplers import ProbabilitySampler
from opencensus.trace.tracer import Tracer

# Configure logging
import logging
logger = logging.getLogger(__name__)
logger.addHandler(AzureLogHandler(
    connection_string='InstrumentationKey=your-key'
))

# Configure tracing
tracer = Tracer(
    exporter=AzureExporter(
        connection_string='InstrumentationKey=your-key'
    ),
    sampler=ProbabilitySampler(1.0)
)
```

### Health Checks

Implement comprehensive health checks:

```python
from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
import asyncio
import sqlalchemy

@app.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {"status": "healthy", "timestamp": time.time()}

@app.get("/ready")
async def readiness_check():
    """Readiness check with dependency validation."""
    checks = {
        "database": await check_database(),
        "azure_ml": await check_azure_ml(),
        "storage": await check_storage()
    }
    
    all_healthy = all(checks.values())
    status_code = status.HTTP_200_OK if all_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
    
    return JSONResponse(
        content={"status": "ready" if all_healthy else "not_ready", "checks": checks},
        status_code=status_code
    )

async def check_database():
    """Check database connectivity."""
    try:
        # Simple query to verify connection
        result = await database.fetch_one("SELECT 1")
        return True
    except Exception:
        return False

async def check_azure_ml():
    """Check Azure ML workspace connectivity."""
    try:
        # Verify workspace access
        from azure.ai.ml import MLClient
        ml_client = MLClient.from_config()
        ml_client.workspace.get()
        return True
    except Exception:
        return False
```

### Metrics Collection

Implement custom metrics:

```python
from prometheus_client import Counter, Histogram, generate_latest
import time

# Define metrics
REQUEST_COUNT = Counter('automl_requests_total', 'Total requests', ['method', 'endpoint'])
REQUEST_DURATION = Histogram('automl_request_duration_seconds', 'Request duration')
EXPERIMENT_COUNT = Counter('automl_experiments_total', 'Total experiments started')

@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    
    response = await call_next(request)
    
    # Record metrics
    REQUEST_COUNT.labels(
        method=request.method, 
        endpoint=request.url.path
    ).inc()
    
    REQUEST_DURATION.observe(time.time() - start_time)
    
    return response

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(generate_latest(), media_type="text/plain")
```

## Performance Optimization

### Database Optimization

1. **Connection pooling**:

```python
from sqlalchemy.pool import QueuePool

engine = create_engine(
    database_url,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True,
    pool_recycle=3600
)
```

2. **Async database operations**:

```python
import asyncpg
from databases import Database

database = Database(database_url)

@app.on_event("startup")
async def startup():
    await database.connect()

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()
```

### Caching

Implement Redis caching for frequently accessed data:

```python
import redis.asyncio as redis
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.decorator import cache

# Configure Redis
redis_client = redis.from_url("redis://localhost:6379")
FastAPICache.init(RedisBackend(redis_client), prefix="automl:")

@app.get("/datasets")
@cache(expire=300)  # Cache for 5 minutes
async def list_datasets():
    # This result will be cached
    return await fetch_datasets_from_db()
```

### Async Processing

Use background tasks for long-running operations:

```python
from fastapi import BackgroundTasks
import asyncio

@app.post("/experiments")
async def start_experiment(experiment_data: dict, background_tasks: BackgroundTasks):
    # Start experiment in background
    background_tasks.add_task(run_experiment_async, experiment_data)
    
    return {"status": "experiment_queued", "experiment_id": experiment_data["id"]}

async def run_experiment_async(experiment_data: dict):
    """Run experiment asynchronously."""
    try:
        # Long-running experiment logic
        result = await run_automl_experiment(experiment_data)
        
        # Update database with results
        await update_experiment_status(experiment_data["id"], "completed", result)
        
    except Exception as e:
        await update_experiment_status(experiment_data["id"], "failed", str(e))
```

## Backup and Disaster Recovery

### Database Backup

1. **Automated backups** in Azure SQL Database:

```bash
# Configure backup retention
az sql db short-term-retention-policy set \
  --resource-group automl-rg \
  --server your-sql-server \
  --database your-database \
  --retention-days 35

# Configure long-term retention
az sql db ltr-policy set \
  --resource-group automl-rg \
  --server your-sql-server \
  --database your-database \
  --weekly-retention P12W \
  --monthly-retention P12M \
  --yearly-retention P5Y
```

2. **Export data for archival**:

```python
import pandas as pd
from azure.storage.blob import BlobServiceClient

async def backup_data_to_blob_storage():
    """Backup critical data to blob storage."""
    blob_client = BlobServiceClient.from_connection_string(connection_string)
    
    # Export datasets metadata
    datasets = await database.fetch_all("SELECT * FROM datasets")
    df = pd.DataFrame(datasets)
    
    # Upload to blob storage
    blob_client.get_blob_client(
        container="backups",
        blob=f"datasets_backup_{datetime.now().isoformat()}.csv"
    ).upload_blob(df.to_csv(index=False))
```

### Application State Backup

1. **Configuration backup**:

```bash
# Backup environment configuration
kubectl get configmap automl-config -o yaml > config-backup.yaml
kubectl get secret automl-secrets -o yaml > secrets-backup.yaml
```

2. **Azure ML artifacts backup**:

```python
from azure.ai.ml import MLClient

ml_client = MLClient.from_config()

# Backup registered models
for model in ml_client.models.list():
    ml_client.models.download(
        name=model.name,
        version=model.version,
        download_path=f"./backups/models/{model.name}"
    )
```

## Scaling Considerations

### Horizontal Scaling

1. **Load balancing**:

```yaml
# Kubernetes HPA
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: automl-api-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: automl-api
  minReplicas: 2
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

2. **Database connection management**:

```python
# Use connection pooling with proper sizing
# Rule of thumb: (number_of_cores * 2) + number_of_disks
POOL_SIZE = min(20, (os.cpu_count() * 2) + 2)

engine = create_engine(
    database_url,
    pool_size=POOL_SIZE,
    max_overflow=10
)
```

### Vertical Scaling

Resource recommendations based on workload:

| Workload Type | CPU | Memory | Replicas |
|--------------|-----|--------|----------|
| Development | 0.5 cores | 1GB | 1 |
| Small Production | 1 core | 2GB | 2-3 |
| Medium Production | 2 cores | 4GB | 3-5 |
| Large Production | 4 cores | 8GB | 5-10 |

## Cost Optimization

### Azure Resource Management

1. **Right-size compute resources**:

```bash
# Use Azure Advisor recommendations
az advisor recommendation list --category Cost

# Monitor resource utilization
az monitor metrics list \
  --resource your-container-app-id \
  --metric "CpuPercentage,MemoryPercentage"
```

2. **Use reserved instances** for predictable workloads:

```bash
# Purchase reserved capacity for SQL Database
az sql db show-usage --ids /subscriptions/.../databases/your-database
```

3. **Implement auto-shutdown** for development environments:

```python
# Scheduled shutdown for non-production
import schedule
import time

def shutdown_dev_resources():
    if os.getenv("ENVIRONMENT") == "development":
        # Scale down resources
        os.system("kubectl scale deployment automl-api --replicas=0")

schedule.every().day.at("18:00").do(shutdown_dev_resources)
```

This deployment guide provides a comprehensive foundation for taking the Azure AutoML API from development to production with proper security, monitoring, and scalability considerations.
