from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_ok():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# Runs against the real Postgres from docker-compose (no mocks): `docker compose up -d postgres`.
def test_health_db_reaches_postgres():
    response = client.get("/health/db")

    assert response.status_code == 200
    assert response.json() == {"database": "ok"}
