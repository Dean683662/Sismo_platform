"""Run a provider sync and persist normalized, idempotent event records."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.database.models import DataSource, IngestionRun, SeismicEvent
from backend.ingestion.base_connector import BaseConnector
from backend.ingestion.normalizer import normalize_igp_event


def sync_source(db: Session, source: DataSource, connector: BaseConnector) -> IngestionRun:
	started_at = datetime.now(timezone.utc)
	run = IngestionRun(source_id=source.id, started_at=started_at, status="running")
	db.add(run)
	source.last_sync_at = started_at
	db.commit()
	db.refresh(run)
	run_id = run.id
	source_id = source.id

	try:
		raw_events = connector.fetch_events()
		run.records_seen = len(raw_events)
		for raw_event in raw_events:
			event = normalize_igp_event(raw_event)
			existing = db.scalar(
				select(SeismicEvent).where(
					SeismicEvent.source_id == source_id,
					SeismicEvent.external_id == event.external_id,
				)
			)
			if existing is not None:
				if existing.payload_hash == event.payload_hash:
					run.records_duplicated += 1
					continue
				for field, value in event.model_dump(exclude={"external_id", "payload_hash"}).items():
					setattr(existing, field, value)
				existing.payload_hash = event.payload_hash
				run.records_updated += 1
				continue

			new_record = SeismicEvent(
				source_id=source_id,
				**event.model_dump(),
			)
			try:
				with db.begin_nested():
					db.add(new_record)
					db.flush()
				run.records_inserted += 1
			except IntegrityError:
				duplicate = db.scalar(
					select(SeismicEvent.id).where(
						SeismicEvent.source_id == source_id,
						SeismicEvent.external_id == event.external_id,
					)
				)
				if duplicate is None:
					raise
				run.records_duplicated += 1

		run.status = "succeeded"
		run.finished_at = datetime.now(timezone.utc)
		source.status = "active"
		source.last_success_at = run.finished_at
		db.commit()
		return run
	except Exception as error:
		db.rollback()
		run = db.get(IngestionRun, run_id)
		source = db.get(DataSource, source_id)
		if run is None or source is None:
			raise
		run.status = "failed"
		run.finished_at = datetime.now(timezone.utc)
		run.error_summary = f"{type(error).__name__}: {str(error)}"[:500]
		source.status = "degraded"
		source.last_sync_at = run.finished_at
		db.commit()
		return run