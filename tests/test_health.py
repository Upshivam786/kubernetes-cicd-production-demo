import os

os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DB_NAME", "testdb")
os.environ.setdefault("DB_USER", "testuser")
os.environ.setdefault("DB_PASSWORD", "testpassword")

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_healthz():
    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
