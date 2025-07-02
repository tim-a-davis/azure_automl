import uuid

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Index,
)
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


def default_uuid():
    return str(uuid.uuid4())


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
        Index("ix_dataset_tenant_name", "tenant_id", "name", unique=True),
    )

    id = Column(UNIQUEIDENTIFIER, primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(255), nullable=False)
    asset_id = Column(String(255))
    name = Column(String(255), nullable=False)
    version = Column(String(50))
    storage_uri = Column(String(1000))
    columns = Column(JSON)
    row_count = Column(Integer)
    byte_size = Column(Integer)
    profile_path = Column(String(1000))


class Experiment(TimestampMixin, Base):
    __tablename__ = "experiments"
    id = Column(UNIQUEIDENTIFIER, primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(255), nullable=False)
    dataset_id = Column(UNIQUEIDENTIFIER, ForeignKey("datasets.id", ondelete="CASCADE"))
    task_type = Column(String(100))
    primary_metric = Column(String(100))


class Run(TimestampMixin, Base):
    __tablename__ = "runs"
    id = Column(UNIQUEIDENTIFIER, primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(255), nullable=False)
    experiment_id = Column(
        UNIQUEIDENTIFIER, ForeignKey("experiments.id", ondelete="CASCADE")
    )
    job_name = Column(String(255))
    queued_at = Column(DateTime)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    metrics = Column(JSON)
    logs_uri = Column(String(1000))
    charts_uri = Column(String(1000))
    best_model_id = Column(
        UNIQUEIDENTIFIER, ForeignKey("models.id", ondelete="SET NULL")
    )


class Model(TimestampMixin, Base):
    __tablename__ = "models"
    __table_args__ = (
        Index("ix_model_tenant_name", "tenant_id", "azure_model_id", unique=True),
    )

    id = Column(UNIQUEIDENTIFIER, primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(255), nullable=False)
    task_type = Column(String(100))
    input_schema = Column(JSON)
    output_schema = Column(JSON)
    azure_model_id = Column(String(255))


class Endpoint(TimestampMixin, Base):
    __tablename__ = "endpoints"
    __table_args__ = (
        Index("ix_endpoint_tenant_id", "tenant_id", "id"),
    )

    id = Column(UNIQUEIDENTIFIER, primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(255), nullable=False)
    deployments = Column(JSON)
    model_id = Column(UNIQUEIDENTIFIER, ForeignKey("models.id", ondelete="CASCADE"))
    blue_traffic = Column(Integer)
    latency = Column(Float)
    error_rate = Column(Float)


class CostRecord(TimestampMixin, Base):
    __tablename__ = "cost_records"
    id = Column(UNIQUEIDENTIFIER, primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(255), nullable=False)
    billing_scope = Column(String(255))
    last_bill = Column(Float)


class Role(TimestampMixin, Base):
    __tablename__ = "roles"
    id = Column(UNIQUEIDENTIFIER, primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False)


class User(TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        Index("ix_user_tenant_name", "tenant_id", "id"),
    )

    id = Column(UNIQUEIDENTIFIER, primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(255), nullable=False)
    role_id = Column(UNIQUEIDENTIFIER, ForeignKey("roles.id", ondelete="SET NULL"))


class AuditEntry(TimestampMixin, Base):
    __tablename__ = "audit_entries"
    __table_args__ = (
        Index("ix_audit_tenant_timestamp", "tenant_id", "created_at"),
    )

    id = Column(UNIQUEIDENTIFIER, primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(255), nullable=False)
    user_id = Column(UNIQUEIDENTIFIER)
    action = Column(String(100))
    diff = Column(JSON)
