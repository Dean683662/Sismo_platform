"""Tests for normalized and idempotent seismic ingestion."""

from collections.abc import Generator
from datetime import timezone

import pytest
import httpx
from pydantic import ValidationError
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.core.database import Base
from backend.database.models import DataSource, IngestionRun, SeismicEvent
from backend.ingestion.base_connector import BaseConnector
from backend.ingestion.igp_connector import IGPConnector
from backend.ingestion.normalizer import normalize_igp_event
from backend.services.ingestion_service import sync_source


IGP_PAYLOAD = {
	"codigo": "2026-0736",
	"numero": 736,
	"fecha_hora": "2026-10-15T15:08:22.000Z",
	"magnitud": "3.8",
	"referencia": "25 km al NE de Tarma, Tarma - Junín",
	"latitud": "-11.26",
	"longitud": "-75.53",
	"profundidad": 15,
	"tipo_evento": "P",
	"simulacro": 0,
	"mapa_sismico_url": "https://www.igp.gob.pe/mapas-tematicos/2026/736/sismo.png",
}


class FixtureConnector(BaseConnector):
	provider_key = "igp"

	def __init__(self, payload: dict) -> None:
		self.payload = payload

	def fetch_events(self) -> list[dict]:
		return [self.payload]


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
	engine = create_engine(
		"sqlite+pysqlite:///:memory:",
		connect_args={"check_same_thread": False},
		poolclass=StaticPool,
	)
	Base.metadata.create_all(engine)
	session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
	session = session_factory()
	session.add(
		DataSource(
			provider_key="igp",
			name="Último sismo reportado",
			organization="Instituto Geofísico del Perú",
			base_url="https://ultimosismo.igp.gob.pe/api/ultimo-sismo",
			source_type="official_api",
		)
	)
	session.commit()
	yield session
	session.close()
	Base.metadata.drop_all(engine)
	engine.dispose()


def test_normalize_verified_igp_payload_to_utc() -> None:
	event = normalize_igp_event(IGP_PAYLOAD)

	assert event.external_id == "2026-0736"
	assert event.occurred_at.tzinfo == timezone.utc
	assert event.latitude == -11.26
	assert event.magnitude == 3.8
	assert len(event.payload_hash) == 64


def test_normalizer_rejects_out_of_range_coordinates() -> None:
	invalid_payload = {**IGP_PAYLOAD, "latitud": "-111.26"}

	with pytest.raises(ValidationError):
		normalize_igp_event(invalid_payload)


def test_igp_connector_accepts_verified_json_and_ignores_simulacros() -> None:
	def handler(request: httpx.Request) -> httpx.Response:
		assert request.headers["accept"] == "application/json"
		return httpx.Response(200, json={"data": [IGP_PAYLOAD, {**IGP_PAYLOAD, "codigo": "drill", "simulacro": "1"}]})

	connector = IGPConnector(endpoint="https://igp.example/api", transport=httpx.MockTransport(handler))

	assert connector.fetch_events() == [IGP_PAYLOAD]


def test_sync_is_idempotent_and_tracks_provider_revisions(db_session: Session) -> None:
	source = db_session.scalar(select(DataSource).where(DataSource.provider_key == "igp"))
	assert source is not None

	first = sync_source(db_session, source, FixtureConnector(IGP_PAYLOAD))
	second = sync_source(db_session, source, FixtureConnector(IGP_PAYLOAD))

	assert first.status == "succeeded"
	assert first.records_inserted == 1
	assert second.records_duplicated == 1
	assert db_session.scalar(select(func.count(SeismicEvent.id))) == 1

	corrected_payload = {**IGP_PAYLOAD, "magnitud": "3.9"}
	third = sync_source(db_session, source, FixtureConnector(corrected_payload))

	assert third.records_updated == 1
	assert db_session.scalar(select(func.count(SeismicEvent.id))) == 1
	assert db_session.scalar(select(SeismicEvent.magnitude)) == 3.9
	assert db_session.scalar(select(func.count(IngestionRun.id))) == 3