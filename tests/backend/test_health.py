from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from backend import main
from backend.main import app


def test_health_endpoints_report_service_status() -> None:
    client = TestClient(app)

    assert client.get("/health").json() == {
        "status": "ok",
        "service": "sismo-platform-api",
    }
    assert client.get("/api/v1/health").status_code == 200
    assert client.get("/health").headers["x-content-type-options"] == "nosniff"


def test_readiness_reports_database_dependency(monkeypatch) -> None:
    class HealthyConnection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def execute(self, statement):
            assert str(statement) == "SELECT 1"

    class HealthyEngine:
        def connect(self):
            return HealthyConnection()

    class UnavailableEngine:
        def connect(self):
            raise SQLAlchemyError("database unavailable")

    client = TestClient(app)
    monkeypatch.setattr(main, "engine", HealthyEngine())
    assert client.get("/ready").json()["status"] == "ready"

    monkeypatch.setattr(main, "engine", UnavailableEngine())
    response = client.get("/ready")
    assert response.status_code == 503
    assert response.json()["dependency"] == "database"