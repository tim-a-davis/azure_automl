import uuid
from sqlalchemy import Column, String, Integer, Float, JSON, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

def default_uuid():
    return str(uuid.uuid4())

class Dataset(Base):
    __tablename__ = 'datasets'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String, nullable=False)
    asset_id = Column(String)
    name = Column(String)
    version = Column(String)
    storage_uri = Column(String)
    columns = Column(JSON)
    row_count = Column(Integer)
    byte_size = Column(Integer)
    profile_path = Column(String)

class Experiment(Base):
    __tablename__ = 'experiments'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String, nullable=False)
    task_type = Column(String)
    primary_metric = Column(String)

class Run(Base):
    __tablename__ = 'runs'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String, nullable=False)
    experiment_id = Column(UUID(as_uuid=True), ForeignKey('experiments.id'))
    job_name = Column(String)
    queued_at = Column(DateTime)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    metrics = Column(JSON)
    logs_uri = Column(String)
    charts_uri = Column(String)
    best_model_id = Column(UUID(as_uuid=True), ForeignKey('models.id'))

class Model(Base):
    __tablename__ = 'models'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String, nullable=False)
    task_type = Column(String)
    input_schema = Column(JSON)
    output_schema = Column(JSON)
    azure_model_id = Column(String)

class Endpoint(Base):
    __tablename__ = 'endpoints'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String, nullable=False)
    deployments = Column(JSON)
    blue_traffic = Column(Integer)
    latency = Column(Float)
    error_rate = Column(Float)

class CostRecord(Base):
    __tablename__ = 'cost_records'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String, nullable=False)
    billing_scope = Column(String)
    last_bill = Column(Float)

class Role(Base):
    __tablename__ = 'roles'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String)

class User(Base):
    __tablename__ = 'users'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String, nullable=False)
    role_id = Column(UUID(as_uuid=True), ForeignKey('roles.id'))

class AuditEntry(Base):
    __tablename__ = 'audit_entries'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String, nullable=False)
    user_id = Column(UUID(as_uuid=True))
    action = Column(String)
    timestamp = Column(DateTime)
    diff = Column(JSON)
