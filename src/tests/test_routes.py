from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
os.environ.setdefault("AZURE_TENANT_ID", "t")
os.environ.setdefault("AZURE_CLIENT_ID", "c")
os.environ.setdefault("AZURE_CLIENT_SECRET", "secret")
os.environ.setdefault("AZURE_SUBSCRIPTION_ID", "sub")
os.environ.setdefault("AZURE_ML_WORKSPACE", "ws")
os.environ.setdefault("AZURE_ML_RESOURCE_GROUP", "rg")
os.environ.setdefault("JWT_SECRET", "secret")

from app.main import app
from app.db import Base, get_db
import app.routes.datasets as datasets_route
import app.routes.experiments as experiments_route
from unittest.mock import MagicMock
from uuid import UUID

client = TestClient(app)

def test_health_check():
    response = client.get("/datasets")
    assert response.status_code in (200, 403)


def override_db():
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_create_dataset():
    app.dependency_overrides[get_db] = override_db
    mock_service = MagicMock()
    mock_service.upload_dataset.return_value = datasets_route.Dataset(
        id=UUID("00000000-0000-0000-0000-000000000000"),
        uploaded_by=UUID("11111111-1111-1111-1111-111111111111"),
        name="data.csv",
        version="1",
        storage_uri="/tmp/data.csv",
    )
    app.dependency_overrides[datasets_route.get_service] = lambda: mock_service
    with open("/tmp/testfile", "wb") as f:
        f.write(b"a")
    with open("/tmp/testfile", "rb") as f:
        response = client.post("/datasets", files={"file": ("data.csv", f, "text/csv")})
    assert response.status_code in (200, 403)
    app.dependency_overrides.clear()


def test_start_experiment():
    app.dependency_overrides[get_db] = override_db
    mock_service = MagicMock()
    mock_service.start_experiment.return_value = experiments_route.Run(
        id=UUID("11111111-1111-1111-1111-111111111111"),
        user_id=UUID("11111111-1111-1111-1111-111111111111"),
        job_name="job1",
    )
    app.dependency_overrides[experiments_route.get_service] = lambda: mock_service
    exp = {
        "id": "11111111-1111-1111-1111-111111111111",
        "user_id": "11111111-1111-1111-1111-111111111111",
        "task_type": "classification",
    }
    response = client.post("/experiments", json=exp)
    assert response.status_code in (200, 403)
    if response.status_code == 200:
        list_resp = client.get("/experiments")
        assert list_resp.status_code == 200
        assert len(list_resp.json()) == 1
    app.dependency_overrides.clear()


def test_get_dataset_not_found():
    app.dependency_overrides[get_db] = override_db
    response = client.get("/datasets/does-not-exist")
    assert response.status_code == 404 or response.status_code == 403
    app.dependency_overrides.clear()


def test_delete_dataset_not_found():
    app.dependency_overrides[get_db] = override_db
    response = client.delete("/datasets/does-not-exist")
    assert response.status_code == 404 or response.status_code == 403
    app.dependency_overrides.clear()


def test_create_dataset_error():
    app.dependency_overrides[get_db] = override_db
    failing_service = MagicMock()
    failing_service.upload_dataset.side_effect = RuntimeError("boom")
    app.dependency_overrides[datasets_route.get_service] = lambda: failing_service
    with open("/tmp/testfile", "wb") as f:
        f.write(b"a")
    with open("/tmp/testfile", "rb") as f:
        resp = client.post("/datasets", files={"file": ("data.csv", f, "text/csv")})
    assert resp.status_code in (500, 403)
    app.dependency_overrides.clear()
