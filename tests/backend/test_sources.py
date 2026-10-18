"""Tests for authorized source synchronization and run tracking."""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.api.v1.endpoints import sources as sources_endpoint
from backend.core.database import Base, get_db
from backend.core.security import hash_password
from backend.database.models import DataSource, Role, User
from backend.main import app


class FixtureConnector:
	provider_key = "igp"

	def fetch_events(self) -> list[dict]:
		return [
			{
				"codigo": "2026-0736",
				"fecha_hora": "2026-10-15T15:08:22.000Z",
				"magnitud": "3.8",
				"referencia": "Tarma, Junín",
				"latitud": "-11.26",
				"longitud": "-75.53",
				"profundidad": 15,
				"simulacro": 0,
			}
		]


class FixtureHistoricalConnector:
	provider_key = "igp"

	def fetch_events(self) -> list[dict]:
		return [
			{
				"codigo": "igp-historical-fixture-1",
				"fecha_hora": "1552-07-02T10:30:00+00:00",
				"magnitud": 7.6,
				"tipo_magnitud": "MB",
				"referencia": "Catálogo histórico IGP (Perú)",
				"latitud": -16.6,
				"longitud": -71.3,
				"profundidad": 30,
				"source_url": "https://ultimosismo.igp.gob.pe/repositorio/datos-sismicos",
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
				full_name="Admin de ingesta",
				email="ingestion-admin@example.com",
				password_hash=hash_password("ClaveIngesta-Segura-123"),
				roles=[admin_role],
			)
		)
		db.add(
			DataSource(
				provider_key="igp",
				name="Catálogo sísmico del IGP",
				organization="Instituto Geofísico del Perú",
				base_url="https://ultimosismo.igp.gob.pe/repositorio/datos-sismicos",
				source_type="official_api",
				is_verified=True,
			)
		)

	def override_get_db() -> Generator:
		db = session_factory()
		try:
			yield db
		finally:
			db.close()

	monkeypatch.setattr(sources_endpoint, "IGPConnector", FixtureConnector)
	monkeypatch.setattr(sources_endpoint, "IGPHistoricalCatalogConnector", FixtureHistoricalConnector)
	app.dependency_overrides[get_db] = override_get_db
	with TestClient(app) as test_client:
		yield test_client
	app.dependency_overrides.clear()
	Base.metadata.drop_all(engine)
	engine.dispose()


def test_manual_sync_requires_csrf_and_records_run(client: TestClient) -> None:
	login = client.post(
		"/api/v1/auth/login",
		json={"email": "ingestion-admin@example.com", "password": "ClaveIngesta-Segura-123"},
	)
	assert login.status_code == 200

	sources = client.get("/api/v1/sources")
	assert sources.status_code == 200
	source = sources.json()[0]

	assert client.post(f"/api/v1/sources/{source['id']}/sync").status_code == 403
	run = client.post(
		f"/api/v1/sources/{source['id']}/sync",
		headers={"X-CSRF-Token": client.cookies.get("sismo_csrf", "")},
	)
	assert run.status_code == 200
	assert run.json()["status"] == "succeeded"
	assert run.json()["records_inserted"] == 1
	assert run.json()["records_skipped"] == 0

	events = client.get("/api/v1/events").json()
	assert events["total"] == 1
	assert events["items"][0]["external_id"] == "2026-0736"

	updated_source = client.get("/api/v1/sources").json()[0]
	assert updated_source["last_run"]["records_inserted"] == 1

	audit = client.get("/api/v1/admin/audit-logs").json()
	assert any(entry["action"] == "ingestion.manual_sync" for entry in audit)


def test_historical_import_requires_csrf_and_skips_alert_delivery(client: TestClient) -> None:
	login = client.post(
		"/api/v1/auth/login",
		json={"email": "ingestion-admin@example.com", "password": "ClaveIngesta-Segura-123"},
	)
	assert login.status_code == 200
	source = client.get("/api/v1/sources").json()[0]
	csrf = client.cookies.get("sismo_csrf", "")

	rule = client.post(
		"/api/v1/alerts/rules",
		headers={"X-CSRF-Token": csrf},
		json={"name": "Umbral histórico", "min_magnitude": 1},
	)
	assert rule.status_code == 201
	assert client.post(f"/api/v1/sources/{source['id']}/backfill").status_code == 403

	run = client.post(
		f"/api/v1/sources/{source['id']}/backfill",
		headers={"X-CSRF-Token": csrf},
	)
	assert run.status_code == 200
	assert run.json()["status"] == "succeeded"
	assert run.json()["records_inserted"] == 1
	assert client.get("/api/v1/alerts/deliveries").json() == []
	assert client.get("/api/v1/events").json()["items"][0]["external_id"] == "igp-historical-fixture-1"

	audit = client.get("/api/v1/admin/audit-logs").json()
	backfill_audit = next(entry for entry in audit if entry["action"] == "ingestion.historical_backfill")
	assert backfill_audit["after_json"]["alerts_dispatched"] is False
	assert backfill_audit["after_json"]["records_skipped"] == 0