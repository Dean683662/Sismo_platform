"""Tests for authenticated event catalog queries."""

from collections.abc import Generator
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.core.database import Base, get_db
from backend.core.security import hash_password
from backend.database.models import DataSource, Role, SeismicEvent, User
from backend.main import app


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
	engine = create_engine(
		"sqlite+pysqlite:///:memory:",
		connect_args={"check_same_thread": False},
		poolclass=StaticPool,
	)
	Base.metadata.create_all(engine)
	session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
	with session_factory.begin() as db:
		reader_role = Role(name="read_only", description="Consulta")
		db.add(reader_role)
		db.flush()
		db.add(
			User(
				full_name="Lector de prueba",
				email="events-reader@example.com",
				password_hash=hash_password("ClaveLectura-Segura-123"),
				roles=[reader_role],
			)
		)
		source = DataSource(
			provider_key="igp",
			name="IGP",
			organization="Instituto Geofísico del Perú",
			base_url="https://ultimosismo.igp.gob.pe/api/ultimo-sismo",
			source_type="official_api",
		)
		db.add(source)
		db.flush()
		for external_id, magnitude, hour in [("2026-01", 2.4, 8), ("2026-02", 4.1, 9)]:
			db.add(
				SeismicEvent(
					external_id=external_id,
					source_id=source.id,
					occurred_at=datetime(2026, 10, 15, hour, tzinfo=timezone.utc),
					latitude=-11.26,
					longitude=-75.53,
					magnitude=magnitude,
					depth_km=15,
					place="Tarma, Junín",
					source_url="https://ultimosismo.igp.gob.pe/ultimo-sismo",
					payload_hash=(external_id * 32)[:64],
				)
			)

	def override_get_db() -> Generator:
		db = session_factory()
		try:
			yield db
		finally:
			db.close()

	app.dependency_overrides[get_db] = override_get_db
	with TestClient(app) as test_client:
		yield test_client
	app.dependency_overrides.clear()
	Base.metadata.drop_all(engine)
	engine.dispose()


def test_event_catalog_requires_authentication(client: TestClient) -> None:
	assert client.get("/api/v1/events").status_code == 401


def test_event_catalog_filters_and_paginates(client: TestClient) -> None:
	login = client.post(
		"/api/v1/auth/login",
		json={"email": "events-reader@example.com", "password": "ClaveLectura-Segura-123"},
	)
	assert login.status_code == 200

	response = client.get("/api/v1/events?min_magnitude=3&limit=1&offset=0")
	assert response.status_code == 200
	assert response.json()["total"] == 1
	assert response.json()["items"][0]["external_id"] == "2026-02"
	assert response.json()["items"][0]["source_key"] == "igp"

	invalid = client.get("/api/v1/events?min_magnitude=5&max_magnitude=2")
	assert invalid.status_code == 422