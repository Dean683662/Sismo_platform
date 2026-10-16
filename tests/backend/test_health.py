from fastapi.testclient import TestClient

from backend.main import app


def test_health_endpoints_report_service_status() -> None:
    client = TestClient(app)

    assert client.get("/health").json() == {
        "status": "ok",
        "service": "sismo-platform-api",
    }
    assert client.get("/api/v1/health").status_code == 200