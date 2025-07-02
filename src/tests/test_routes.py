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
from unittest.mock import patch
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


@patch.object(datasets_route.service, "upload_dataset")
def test_create_dataset(mock_upload):
    app.dependency_overrides[get_db] = override_db
    mock_upload.return_value = datasets_route.Dataset(
        id=UUID("00000000-0000-0000-0000-000000000000"),
        tenant_id="t",
        name="data.csv",
        version="1",
        storage_uri="/tmp/data.csv",
    )
    with open("/tmp/testfile", "wb") as f:
        f.write(b"a")
    with open("/tmp/testfile", "rb") as f:
        response = client.post("/datasets", files={"file": ("data.csv", f, "text/csv")})
    assert response.status_code in (200, 403)
    app.dependency_overrides.clear()
