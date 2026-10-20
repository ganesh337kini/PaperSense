from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "app" in data


def test_db_health():
    response = client.get("/api/db-health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "connected"
    assert "tables" in data
    assert "papers" in data["tables"]
