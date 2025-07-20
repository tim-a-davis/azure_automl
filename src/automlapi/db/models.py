import uuid

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    TypeDecorator,
)
from sqlalchemy import String as SQLString
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER
from sqlalchemy.sql import func

from . import Base


def default_uuid():
    return str(uuid.uuid4())


class UUID(TypeDecorator):
    """Cross-database UUID type that works with both SQLite and SQL Server."""

    impl = SQLString
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "sqlite":
            return dialect.type_descriptor(SQLString(36))
        elif dialect.name == "mssql":
            return dialect.type_descriptor(UNIQUEIDENTIFIER())
        else:
            return dialect.type_descriptor(SQLString(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif isinstance(value, uuid.UUID):
            return str(value)
        else:
            return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            return str(value)


class TimestampMixin:
    """Mixin providing created/updated timestamps."""

    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class Dataset(TimestampMixin, Base):
    __tablename__ = "datasets"
    __table_args__ = (
        Index("ix_dataset_uploaded_by", "uploaded_by"),
        Index(
            "ix_dataset_name_version",
            "name",
            "version",
            unique=True,
        ),
    )

    id = Column(UUID, primary_key=True, default=default_uuid)
    uploaded_by = Column(UUID, nullable=False)  # User ID who uploaded the dataset
    asset_id = Column(String(255))
    name = Column(String(255), nullable=False)
    version = Column(String(50))
    storage_uri = Column(String(1000))
    columns = Column(JSON)
    row_count = Column(Integer)
    byte_size = Column(Integer)
    profile_path = Column(String(1000))
    tags = Column(JSON)  # Store tags for categorization and search
    private = Column(
        Boolean, nullable=False, default=False
    )  # Whether dataset is private


class Experiment(TimestampMixin, Base):
    __tablename__ = "experiments"
    id = Column(UUID, primary_key=True, default=default_uuid)
    user_id = Column(UUID, nullable=True)  # User who created the experiment
    dataset_id = Column(UUID, ForeignKey("datasets.id", ondelete="CASCADE"))
    task_type = Column(String(100))
    primary_metric = Column(String(100))

    # AutoML limit settings
    enable_early_termination = Column(
        String(10)
    )  # 'true'/'false' for cross-database compatibility
    exit_score = Column(Float)
    max_concurrent_trials = Column(Integer, default=20)
    max_cores_per_trial = Column(Integer)
    max_nodes = Column(Integer, default=10)
    max_trials = Column(Integer, default=300)
    timeout_minutes = Column(Integer)
    trial_timeout_minutes = Column(Integer, default=15)


class Run(TimestampMixin, Base):
    __tablename__ = "runs"
    id = Column(UUID, primary_key=True, default=default_uuid)
    user_id = Column(UUID, nullable=True)  # User who started the run
    experiment_id = Column(UUID, ForeignKey("experiments.id", ondelete="CASCADE"))
    job_name = Column(String(255))
    queued_at = Column(DateTime)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    metrics = Column(JSON)
    logs_uri = Column(String(1000))
    charts_uri = Column(String(1000))
    best_model_id = Column(UUID, ForeignKey("models.id", ondelete="SET NULL"))


class Model(TimestampMixin, Base):
    __tablename__ = "models"
    __table_args__ = (
        Index("ix_models_user_id", "user_id"),
        Index("ix_models_run_id", "run_id"),
        Index("ix_models_experiment_id", "experiment_id"),
        Index("ix_models_azure_model", "azure_model_name", "azure_model_version"),
    )

    id = Column(UUID, primary_key=True, default=default_uuid)
    user_id = Column(UUID, nullable=False)  # User who registered the model
    dataset_id = Column(UUID, ForeignKey("datasets.id", ondelete="SET NULL"))
    experiment_id = Column(UUID, ForeignKey("experiments.id", ondelete="CASCADE"))
    run_id = Column(UUID, ForeignKey("runs.id", ondelete="CASCADE"))
    task_type = Column(String(100))
    algorithm = Column(String(255))  # LightGBM, XGBoost, etc.
    azure_model_name = Column(String(255))  # Name in Azure ML model registry
    azure_model_version = Column(String(50))  # Version in Azure ML
    model_uri = Column(String(1000))  # Full Azure ML model URI
    best_score = Column(Float)  # Primary metric score
    performance_metrics = Column(JSON)  # All performance metrics
    model_metadata = Column(JSON)  # Comprehensive model metadata
    input_schema = Column(JSON)
    output_schema = Column(JSON)
    registration_status = Column(String(50), default="pending")
    error_message = Column(String(1000))  # For registration failures
    # Keep existing field for backward compatibility
    azure_model_id = Column(String(255))


class Endpoint(TimestampMixin, Base):
    __tablename__ = "endpoints"
    __table_args__ = (Index("ix_endpoint_user_id", "user_id", "id"),)

    id = Column(UUID, primary_key=True, default=default_uuid)
    user_id = Column(UUID, nullable=True)  # User who created the endpoint
    name = Column(String(255))
    azure_endpoint_name = Column(String(255))
    azure_endpoint_url = Column(String(500))
    auth_mode = Column(String(50), default="key")
    provisioning_state = Column(String(50))
    description = Column(String(1000))
    dataset_id = Column(UUID, ForeignKey("datasets.id", ondelete="SET NULL"))
    experiment_id = Column(UUID, ForeignKey("experiments.id", ondelete="SET NULL"))
    run_id = Column(UUID, ForeignKey("runs.id", ondelete="SET NULL"))
    deployment_status = Column(String(50), default="creating")
    deployment_metadata = Column(JSON)
    endpoint_metadata = Column(JSON)
    deployments = Column(JSON)
    traffic = Column(JSON)
    tags = Column(JSON)
    model_id = Column(UUID, ForeignKey("models.id", ondelete="CASCADE"))
    blue_traffic = Column(Integer)
    latency = Column(Float)
    error_rate = Column(Float)


class Deployment(TimestampMixin, Base):
    __tablename__ = "deployments"
    __table_args__ = (
        Index("ix_deployments_endpoint_id", "endpoint_id"),
        Index("ix_deployments_model_id", "model_id"),
        Index("ix_deployments_user_id", "user_id"),
        Index(
            "ix_deployment_name_endpoint", "endpoint_id", "deployment_name", unique=True
        ),
    )

    id = Column(UUID, primary_key=True, default=default_uuid)
    user_id = Column(UUID, nullable=False)
    endpoint_id = Column(UUID, ForeignKey("endpoints.id", ondelete="CASCADE"))
    model_id = Column(UUID, ForeignKey("models.id", ondelete="CASCADE"))
    deployment_name = Column(String(255), nullable=False)
    azure_deployment_name = Column(String(255))
    instance_type = Column(String(100), default="Standard_DS3_v2")
    instance_count = Column(Integer, default=1)
    traffic_percentage = Column(Integer, default=0)
    deployment_status = Column(String(50), default="creating")
    provisioning_state = Column(String(50))
    deployment_config = Column(JSON)
    error_message = Column(String(1000))


class CostRecord(TimestampMixin, Base):
    __tablename__ = "cost_records"
    id = Column(UUID, primary_key=True, default=default_uuid)
    tenant_id = Column(String(255), nullable=False)
    billing_scope = Column(String(255))
    last_bill = Column(Float)


class Role(TimestampMixin, Base):
    __tablename__ = "roles"
    id = Column(UUID, primary_key=True, default=default_uuid)
    name = Column(String(100), unique=True, nullable=False)


class User(TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (Index("ix_user_id", "id"),)

    id = Column(UUID, primary_key=True, default=default_uuid)
    role_id = Column(UUID, ForeignKey("roles.id", ondelete="SET NULL"))


class AuditEntry(TimestampMixin, Base):
    __tablename__ = "audit_entries"
    __table_args__ = (Index("ix_audit_tenant_timestamp", "tenant_id", "created_at"),)

    id = Column(UUID, primary_key=True, default=default_uuid)
    tenant_id = Column(String(255), nullable=False)
    user_id = Column(UUID)
    action = Column(String(100))
    diff = Column(JSON)
    __tablename__ = "audit_entries"
    __table_args__ = (Index("ix_audit_tenant_timestamp", "tenant_id", "created_at"),)
