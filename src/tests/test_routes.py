from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/datasets")
    assert response.status_code in (200, 403)
