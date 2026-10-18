"""Authenticated API coverage for analytics, datasets, and experiments."""

from collections.abc import Generator
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
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
		administrator = Role(name="administrator", description="Administración")
		db.add(administrator)
		db.flush()
		db.add(
			User(
				full_name="Admin de prueba",
				email="analytics-admin@example.com",
				password_hash=hash_password("ClaveAdmin-Segura-123"),
				roles=[administrator],
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
		start = datetime(2026, 1, 1, tzinfo=timezone.utc)
		for index in range(20):
			db.add(
				SeismicEvent(
					external_id=f"test-{index}", source_id=source.id,
					occurred_at=start + timedelta(days=index), latitude=-10 + index / 10,
					longitude=-75 + index / 20, magnitude=2 + index / 10,
					depth_km=5 + index, place="Perú", payload_hash=f"{index:064x}",
				)
			)

	def override_get_db() -> Generator:
		db = session_factory()
		try:
			yield db
		finally:
			db.close()

	app.dependency_overrides[get_db] = override_get_db
	app.state.analytics_test_session_factory = session_factory
	with TestClient(app) as test_client:
		test_client.post(
			"/api/v1/auth/login",
			json={"email": "analytics-admin@example.com", "password": "ClaveAdmin-Segura-123"},
		)
		yield test_client
	app.dependency_overrides.clear()
	del app.state.analytics_test_session_factory
	Base.metadata.drop_all(engine)
	engine.dispose()


def test_dashboard_timeseries_and_geojson_share_event_data(client: TestClient) -> None:
	summary = client.get("/api/v1/dashboard/summary")
	assert summary.status_code == 200
	assert summary.json()["total_events"] == 20
	assert summary.json()["active_sources"] == 1

	series = client.get(
		"/api/v1/analytics/timeseries",
		params={"start_date": "2026-01-01T00:00:00Z", "end_date": "2026-01-31T00:00:00Z", "group_by": "week"},
	)
	assert series.status_code == 200
	assert series.json()["total_events"] == 20
	assert sum(point["event_count"] for point in series.json()["items"]) == 20

	geojson = client.get("/api/v1/events/geojson?limit=3")
	assert geojson.status_code == 200
	assert len(geojson.json()["features"]) == 3
	assert geojson.json()["features"][0]["geometry"]["coordinates"] == [-74.05, -8.1]


def test_geojson_applies_time_magnitude_and_geographic_filters(client: TestClient) -> None:
	response = client.get(
		"/api/v1/events/geojson",
		params={
			"start_date": "2026-01-10T00:00:00Z",
			"end_date": "2026-01-20T00:00:00Z",
			"min_magnitude": 2.9,
			"max_magnitude": 3.5,
			"min_latitude": -9.1,
			"max_latitude": -8.5,
			"min_longitude": -74.8,
			"max_longitude": -74.4,
		},
	)
	assert response.status_code == 200
	features = response.json()["features"]
	assert len(features) == 4
	assert all(2.9 <= item["properties"]["magnitude"] <= 3.5 for item in features)
	assert all(-9.1 <= item["geometry"]["coordinates"][1] <= -8.5 for item in features)


def test_geojson_rejects_partial_or_inverted_geographic_bounds(client: TestClient) -> None:
	partial = client.get("/api/v1/events/geojson", params={"min_latitude": -10})
	inverted = client.get(
		"/api/v1/events/geojson",
		params={"min_latitude": 5, "max_latitude": -5, "min_longitude": -80, "max_longitude": -70},
	)
	assert partial.status_code == 422
	assert inverted.status_code == 422


def test_dataset_snapshot_versions_and_trains_experiment(client: TestClient) -> None:
	csrf = client.cookies.get("sismo_csrf", "")
	body = {"name": "Magnitudes observadas"}
	dataset = client.post("/api/v1/datasets", json=body, headers={"X-CSRF-Token": csrf})
	assert dataset.status_code == 201
	assert dataset.json()["row_count"] == 20
	assert dataset.json()["version"] == 1
	assert dataset.json()["quality_report"]["rows_valid"] == 20

	second_version = client.post("/api/v1/datasets", json=body, headers={"X-CSRF-Token": csrf})
	assert second_version.json()["version"] == 2
	quality = client.get(f"/api/v1/datasets/{dataset.json()['id']}/quality")
	assert quality.json()["duplicates"] == 0

	experiment = client.post(
		"/api/v1/ml/experiments",
		json={"name": "Baseline temporal", "dataset_id": dataset.json()["id"]},
		headers={"X-CSRF-Token": csrf},
	)
	assert experiment.status_code == 201
	assert experiment.json()["status"] == "completed"
	assert experiment.json()["validation_spec"]["strategy"] == "chronological_holdout"
	assert experiment.json()["validation_spec"]["evaluation_period"][0] > experiment.json()["validation_spec"]["train_period"][1]
	assert "No predice terremotos futuros" in experiment.json()["limitations"]
	assert len(client.get("/api/v1/ml/experiments").json()) == 1


def test_training_rejects_too_small_dataset(client: TestClient) -> None:
	csrf = client.cookies.get("sismo_csrf", "")
	dataset = client.post(
		"/api/v1/datasets",
		json={
			"name": "Muestra insuficiente",
			"start_date": "2026-01-01T00:00:00Z",
			"end_date": "2026-01-01T00:00:00Z",
		},
		headers={"X-CSRF-Token": csrf},
	)
	assert dataset.status_code == 201
	assert dataset.json()["row_count"] == 1

	response = client.post(
		"/api/v1/ml/experiments",
		json={"name": "No entrenar", "dataset_id": dataset.json()["id"]},
		headers={"X-CSRF-Token": csrf},
	)
	assert response.status_code == 422
	assert "five valid" in response.json()["detail"]


def test_classification_experiment_is_available_through_the_api(client: TestClient) -> None:
	with app.state.analytics_test_session_factory() as db:
		events = db.scalars(select(SeismicEvent).order_by(SeismicEvent.occurred_at)).all()
		for index, event in enumerate(events):
			event.magnitude = [3.0, 4.5, 5.5][index % 3]
		db.commit()

	csrf = client.cookies.get("sismo_csrf", "")
	dataset = client.post(
		"/api/v1/datasets",
		json={"name": "Bandas reportadas"},
		headers={"X-CSRF-Token": csrf},
	)
	assert dataset.status_code == 201
	experiment = client.post(
		"/api/v1/ml/experiments",
		json={
			"name": "Clasificación temporal",
			"dataset_id": dataset.json()["id"],
			"task_type": "classification",
		},
		headers={"X-CSRF-Token": csrf},
	)
	assert experiment.status_code == 201
	assert experiment.json()["task_type"] == "classification"
	assert experiment.json()["target_name"] == "reported_magnitude_band"
	assert len(experiment.json()["validation_spec"]["confusion_matrix"]) == 3
	assert experiment.json()["params"]["library_versions"]["scikit_learn"]