"""Integration coverage for operational alerts, report snapshots, and retention controls."""

from collections.abc import Generator
from datetime import datetime, timezone
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from openpyxl import load_workbook
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from pydantic import SecretStr

from backend.api.v1.endpoints import sources as sources_endpoint
from backend.api.v1.endpoints.reports import _spreadsheet_safe
from backend.core.config import settings
from backend.core.database import Base, get_db
from backend.core.security import hash_password
from backend.database.models import DataSource, Role, SeismicEvent, User
from backend.main import app


class FixtureConnector:
	provider_key = "igp"

	def fetch_events(self) -> list[dict]:
		return [
			{
				"codigo": "alert-test-event",
				"fecha_hora": "2026-10-17T12:08:22.000Z",
				"magnitud": "4.8",
				"referencia": "Tarma, Junín",
				"latitud": "-11.26",
				"longitud": "-75.53",
				"profundidad": 15,
				"simulacro": 0,
			}
		]


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient, None, None]:
	engine = create_engine(
		"sqlite+pysqlite:///:memory:",
		connect_args={"check_same_thread": False},
		poolclass=StaticPool,
	)
	Base.metadata.create_all(engine)
	session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
	with session_factory.begin() as db:
		admin_role = Role(name="administrator", description="Administración")
		db.add(admin_role)
		db.flush()
		db.add(
			User(
				full_name="Admin de alertas",
				email="alerts-admin@example.com",
				password_hash=hash_password("ClaveAlertas-Segura-123"),
				roles=[admin_role],
			)
		)
		source = DataSource(
			provider_key="igp",
			name="Último sismo reportado",
			organization="Instituto Geofísico del Perú",
			base_url="https://ultimosismo.igp.gob.pe/api/ultimo-sismo",
			source_type="official_api",
			is_verified=True,
		)
		db.add(source)
		db.flush()
		db.add(
			SeismicEvent(
				external_id="seed-event",
				source_id=source.id,
				occurred_at=datetime(2026, 10, 17, 11, tzinfo=timezone.utc),
				latitude=-11.26,
				longitude=-75.53,
				magnitude=4.2,
				depth_km=15,
				place="Tarma, Junín",
				source_url=source.base_url,
				payload_hash="a" * 64,
			)
		)

	def override_get_db() -> Generator:
		db = session_factory()
		try:
			yield db
		finally:
			db.close()

	monkeypatch.setattr(sources_endpoint, "IGPConnector", FixtureConnector)
	app.dependency_overrides[get_db] = override_get_db
	with TestClient(app) as test_client:
		test_client.post(
			"/api/v1/auth/login",
			json={"email": "alerts-admin@example.com", "password": "ClaveAlertas-Segura-123"},
		)
		yield test_client
	app.dependency_overrides.clear()
	Base.metadata.drop_all(engine)
	engine.dispose()


def test_verified_ingestion_creates_deduplicated_alert_and_requires_approval(client: TestClient) -> None:
	csrf = client.cookies.get("sismo_csrf", "")
	source_id = client.get("/api/v1/sources").json()[0]["id"]
	created = client.post(
		"/api/v1/alerts/rules",
		headers={"X-CSRF-Token": csrf},
		json={
			"name": "Magnitud significativa",
			"min_magnitude": 4,
			"min_depth_km": 10,
			"region_bounds": {
				"min_latitude": -12,
				"max_latitude": -10,
				"min_longitude": -76,
				"max_longitude": -75,
			},
			"source_ids": [source_id],
			"requires_approval": True,
		},
	)
	assert created.status_code == 201
	assert client.post(f"/api/v1/sources/{source_id}/sync", headers={"X-CSRF-Token": csrf}).json()["status"] == "succeeded"

	deliveries = client.get("/api/v1/alerts/deliveries").json()
	assert len(deliveries) == 1
	assert deliveries[0]["status"] == "pending_approval"
	assert deliveries[0]["source_name"] == "Último sismo reportado"
	assert deliveries[0]["event_magnitude"] == pytest.approx(4.8)

	client.post(f"/api/v1/sources/{source_id}/sync", headers={"X-CSRF-Token": csrf})
	assert len(client.get("/api/v1/alerts/deliveries").json()) == 1

	delivery_id = deliveries[0]["id"]
	approved = client.post(
		f"/api/v1/alerts/deliveries/{delivery_id}/approve",
		headers={"X-CSRF-Token": csrf},
	)
	assert approved.status_code == 200
	assert approved.json()["status"] == "delivered"
	assert approved.json()["attempt_count"] == 1
	assert approved.json()["reviewed_at"] is not None


def test_alert_rules_validate_templates_and_tests_use_a_real_source_event(client: TestClient) -> None:
	csrf = client.cookies.get("sismo_csrf", "")
	invalid = client.post(
		"/api/v1/alerts/rules",
		headers={"X-CSRF-Token": csrf},
		json={"name": "Inválida", "min_magnitude": 3, "template": "{untrusted_field}"},
	)
	assert invalid.status_code == 422

	rule = client.post(
		"/api/v1/alerts/rules",
		headers={"X-CSRF-Token": csrf},
		json={"name": "Prueba interna", "min_magnitude": 9},
	)
	assert rule.status_code == 201
	test_delivery = client.post(
		f"/api/v1/alerts/rules/{rule.json()['id']}/test",
		headers={"X-CSRF-Token": csrf},
		json={},
	)
	assert test_delivery.status_code == 201
	assert test_delivery.json()["is_test"] is True
	assert test_delivery.json()["event_id"] == client.get("/api/v1/events").json()["items"][0]["id"]


def test_report_snapshots_export_and_retention_settings_are_audited(client: TestClient) -> None:
	csrf = client.cookies.get("sismo_csrf", "")
	report = client.post(
		"/api/v1/reports",
		headers={"X-CSRF-Token": csrf},
		json={"report_type": "events", "min_magnitude": 4, "limit": 100},
	)
	assert report.status_code == 201
	assert report.json()["row_count"] == 1
	assert report.json()["filters"]["cutoff_at"]

	csv_export = client.get(f"/api/v1/reports/{report.json()['id']}/export?format=csv")
	assert csv_export.status_code == 200
	assert csv_export.headers["content-type"].startswith("text/csv")
	assert "external_id" in csv_export.text
	json_export = client.get(f"/api/v1/reports/{report.json()['id']}/export?format=json")
	assert json_export.json()["records"][0]["external_id"] == "seed-event"
	xlsx_export = client.get(f"/api/v1/reports/{report.json()['id']}/export?format=xlsx")
	assert xlsx_export.status_code == 200
	workbook = load_workbook(BytesIO(xlsx_export.content), read_only=True)
	assert workbook["Datos"]["A1"].value == "id"
	assert workbook["Metadatos"]["B6"].value == report.json()["filters"]["cutoff_at"]
	pdf_export = client.get(f"/api/v1/reports/{report.json()['id']}/export?format=pdf")
	assert pdf_export.status_code == 200
	assert pdf_export.content.startswith(b"%PDF-")
	dataset = client.post(
		"/api/v1/datasets",
		headers={"X-CSRF-Token": csrf},
		json={"name": "Snapshot de calidad"},
	)
	assert dataset.status_code == 201
	quality_report = client.post(
		"/api/v1/reports",
		headers={"X-CSRF-Token": csrf},
		json={"report_type": "quality"},
	)
	assert quality_report.status_code == 201
	assert quality_report.json()["row_count"] == 1
	quality_data = client.get(f"/api/v1/reports/{quality_report.json()['id']}/export?format=json")
	assert quality_data.json()["records"][0]["quality_report"]["rows_valid"] == 1
	assert len(client.get("/api/v1/reports").json()) == 2

	settings = client.patch(
		"/api/v1/admin/settings",
		headers={"X-CSRF-Token": csrf},
		json={
			"audit_retention_days": 180,
			"alert_history_retention_days": 90,
			"report_retention_days": 180,
		},
	)
	assert settings.status_code == 200
	assert settings.json() == {
		"audit_retention_days": 180,
		"alert_history_retention_days": 90,
		"report_retention_days": 180,
	}
	cleanup = client.post("/api/v1/admin/retention/run", headers={"X-CSRF-Token": csrf})
	assert cleanup.status_code == 200
	assert cleanup.json()["status"] == "completed"
	assert cleanup.json()["deleted_report_snapshots"] == 0
	assert any(item["action"] == "reports.snapshot_created" for item in client.get("/api/v1/admin/audit-logs").json())


@pytest.mark.parametrize("value", ["=1+1", " +SUM(A1:A2)", "\t@SUM(A1:A2)", "-42"])
def test_spreadsheet_export_neutralizes_formula_prefixes(value: str) -> None:
	assert _spreadsheet_safe(value).startswith("'")


def test_webhook_delivery_uses_idempotency_and_persists_outcomes(
	client: TestClient,
	monkeypatch: pytest.MonkeyPatch,
) -> None:
	from backend.services import alert_service

	monkeypatch.setattr(settings, "alert_webhook_url", SecretStr("https://receiver.example/alerts"))
	calls: list[tuple[dict, str]] = []
	monkeypatch.setattr(
		alert_service,
		"send_alert_webhook",
		lambda payload, key: calls.append((payload, key)) or None,
	)
	csrf = client.cookies.get("sismo_csrf", "")
	rule = client.post(
		"/api/v1/alerts/rules",
		headers={"X-CSRF-Token": csrf},
		json={"name": "Webhook de prueba", "min_magnitude": 4, "channel": "webhook", "requires_approval": True},
	)
	assert rule.status_code == 201
	source_id = client.get("/api/v1/sources").json()[0]["id"]
	sync = client.post(f"/api/v1/sources/{source_id}/sync", headers={"X-CSRF-Token": csrf})
	assert sync.json()["status"] == "succeeded"
	delivery = client.get("/api/v1/alerts/deliveries").json()[0]
	assert delivery["status"] == "pending_approval"
	assert calls == []
	approved = client.post(
		f"/api/v1/alerts/deliveries/{delivery['id']}/approve",
		headers={"X-CSRF-Token": csrf},
	)
	assert approved.status_code == 200
	assert approved.json()["status"] == "delivered"
	assert approved.json()["attempt_count"] == 1
	assert calls[0][0]["event"]["external_id"] == "alert-test-event"
	assert calls[0][0]["is_test"] is False
	assert calls[0][0]["deduplication_key"] == calls[0][1]
	assert client.get("/api/v1/admin/audit-logs").json()


def test_webhook_failure_can_be_retried_only_within_three_total_attempts(
	client: TestClient,
	monkeypatch: pytest.MonkeyPatch,
) -> None:
	from backend.services import alert_service

	monkeypatch.setattr(settings, "alert_webhook_url", SecretStr("https://receiver.example/alerts"))
	monkeypatch.setattr(alert_service, "send_alert_webhook", lambda payload, key: "http_status_503")
	csrf = client.cookies.get("sismo_csrf", "")
	rule = client.post(
		"/api/v1/alerts/rules",
		headers={"X-CSRF-Token": csrf},
		json={"name": "Webhook con error", "min_magnitude": 4, "channel": "webhook"},
	)
	assert rule.status_code == 201
	source_id = client.get("/api/v1/sources").json()[0]["id"]
	client.post(f"/api/v1/sources/{source_id}/sync", headers={"X-CSRF-Token": csrf})
	delivery = client.get("/api/v1/alerts/deliveries").json()[0]
	assert delivery["status"] == "failed"
	assert delivery["attempt_count"] == 1
	delivery_id = delivery["id"]

	for expected_attempts in (2, 3):
		retried = client.post(
			f"/api/v1/alerts/deliveries/{delivery_id}/retry",
			headers={"X-CSRF-Token": csrf},
		)
		assert retried.status_code == 200
		assert retried.json()["status"] == "failed"
		assert retried.json()["attempt_count"] == expected_attempts
	assert client.post(
		f"/api/v1/alerts/deliveries/{delivery_id}/retry",
		headers={"X-CSRF-Token": csrf},
	).status_code == 409


def test_webhook_rules_require_server_configuration(
	client: TestClient,
	monkeypatch: pytest.MonkeyPatch,
) -> None:
	monkeypatch.setattr(settings, "alert_webhook_url", None)
	response = client.post(
		"/api/v1/alerts/rules",
		headers={"X-CSRF-Token": client.cookies.get("sismo_csrf", "")},
		json={"name": "Webhook sin URL", "min_magnitude": 4, "channel": "webhook"},
	)
	assert response.status_code == 503
	assert "ALERT_WEBHOOK_URL" in response.json()["detail"]
