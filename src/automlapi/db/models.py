import uuid

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


def default_uuid():
    return str(uuid.uuid4())


class Dataset(Base):
    __tablename__ = "datasets"
    id = Column(UNIQUEIDENTIFIER, primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(255), nullable=False)
    asset_id = Column(String(255))
    name = Column(String(255))
    version = Column(String(50))
    storage_uri = Column(String(1000))
    columns = Column(JSON)
    row_count = Column(Integer)
    byte_size = Column(Integer)
    profile_path = Column(String(1000))


class Experiment(Base):
    __tablename__ = "experiments"
    id = Column(UNIQUEIDENTIFIER, primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(255), nullable=False)
    task_type = Column(String(100))
    primary_metric = Column(String(100))


class Run(Base):
    __tablename__ = "runs"
    id = Column(UNIQUEIDENTIFIER, primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(255), nullable=False)
    experiment_id = Column(UNIQUEIDENTIFIER, ForeignKey("experiments.id"))
    job_name = Column(String(255))
    queued_at = Column(DateTime)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    metrics = Column(JSON)
    logs_uri = Column(String(1000))
    charts_uri = Column(String(1000))
    best_model_id = Column(UNIQUEIDENTIFIER, ForeignKey("models.id"))


class Model(Base):
    __tablename__ = "models"
    id = Column(UNIQUEIDENTIFIER, primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(255), nullable=False)
    task_type = Column(String(100))
    input_schema = Column(JSON)
    output_schema = Column(JSON)
    azure_model_id = Column(String(255))


class Endpoint(Base):
    __tablename__ = "endpoints"
    id = Column(UNIQUEIDENTIFIER, primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(255), nullable=False)
    deployments = Column(JSON)
    blue_traffic = Column(Integer)
    latency = Column(Float)
    error_rate = Column(Float)


class CostRecord(Base):
    __tablename__ = "cost_records"
    id = Column(UNIQUEIDENTIFIER, primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(255), nullable=False)
    billing_scope = Column(String(255))
    last_bill = Column(Float)


class Role(Base):
    __tablename__ = "roles"
    id = Column(UNIQUEIDENTIFIER, primary_key=True, default=uuid.uuid4)
    name = Column(String(100))


class User(Base):
    __tablename__ = "users"
    id = Column(UNIQUEIDENTIFIER, primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(255), nullable=False)
    role_id = Column(UNIQUEIDENTIFIER, ForeignKey("roles.id"))


class AuditEntry(Base):
    __tablename__ = "audit_entries"
    id = Column(UNIQUEIDENTIFIER, primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(255), nullable=False)
    user_id = Column(UNIQUEIDENTIFIER)
    action = Column(String(100))
    timestamp = Column(DateTime)
    diff = Column(JSON)
    diff = Column(JSON)
