"""Source catalog and authorized manual synchronization endpoint."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.api.v1.schemas import DataSourceResponse, IngestionRunSummary, SyncRunResponse
from backend.core.database import get_db
from backend.core.security import require_csrf, require_permissions
from backend.database.models import DataSource, IngestionRun, User
from backend.ingestion.igp_connector import IGPConnector
from backend.ingestion.igp_historical_connector import IGPHistoricalCatalogConnector
from backend.services.audit_service import record_audit
from backend.services.ingestion_service import sync_source


router = APIRouter(prefix="/sources", tags=["sources"])


def _run_summary(run: IngestionRun | None) -> IngestionRunSummary | None:
	if run is None:
		return None
	return IngestionRunSummary(
		id=str(run.id), started_at=run.started_at, finished_at=run.finished_at, status=run.status,
		records_seen=run.records_seen, records_inserted=run.records_inserted,
		records_updated=run.records_updated, records_duplicated=run.records_duplicated,
		records_skipped=run.records_skipped,
		error_summary=run.error_summary,
	)


def _source_response(db: Session, source: DataSource) -> DataSourceResponse:
	last_run = db.scalar(
		select(IngestionRun).where(IngestionRun.source_id == source.id).order_by(IngestionRun.started_at.desc()).limit(1)
	)
	return DataSourceResponse(
		id=str(source.id), provider_key=source.provider_key, name=source.name,
		organization=source.organization, base_url=source.base_url, source_type=source.source_type,
		is_verified=source.is_verified, status=source.status, last_sync_at=source.last_sync_at,
		last_success_at=source.last_success_at, last_run=_run_summary(last_run),
	)


@router.get("", response_model=list[DataSourceResponse])
def list_sources(
	db: Session = Depends(get_db),
	_: User = Depends(require_permissions("sources:read")),
) -> list[DataSourceResponse]:
	sources = db.scalars(select(DataSource).order_by(DataSource.name)).all()
	return [_source_response(db, source) for source in sources]


@router.post("/{source_id}/sync", response_model=SyncRunResponse, dependencies=[Depends(require_csrf)])
def sync_data_source(
	source_id: UUID,
	db: Session = Depends(get_db),
	actor: User = Depends(require_permissions("sources:manage")),
) -> SyncRunResponse:
	source = db.get(DataSource, source_id)
	if source is None:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Data source not found")
	if source.provider_key != "igp":
		raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="No connector is configured for this provider")

	run = sync_source(db, source, IGPConnector())
	record_audit(
		db,
		actor_id=actor.id,
		action="ingestion.manual_sync",
		entity_type="data_source",
		entity_id=source.id,
		after={
			"run_id": str(run.id), "status": run.status, "records_seen": run.records_seen,
			"records_inserted": run.records_inserted, "records_updated": run.records_updated,
			"records_duplicated": run.records_duplicated, "records_skipped": run.records_skipped,
		},
	)
	db.commit()
	return SyncRunResponse(
		id=str(run.id), source_id=str(source.id), started_at=run.started_at,
		finished_at=run.finished_at, status=run.status, records_seen=run.records_seen,
		records_inserted=run.records_inserted, records_updated=run.records_updated,
		records_duplicated=run.records_duplicated, records_skipped=run.records_skipped,
		error_summary=run.error_summary,
	)


@router.post("/{source_id}/backfill", response_model=SyncRunResponse, dependencies=[Depends(require_csrf)])
def import_historical_catalog(
	source_id: UUID,
	db: Session = Depends(get_db),
	actor: User = Depends(require_permissions("sources:manage")),
) -> SyncRunResponse:
	source = db.get(DataSource, source_id)
	if source is None:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Data source not found")
	if source.provider_key != "igp":
		raise HTTPException(
			status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
			detail="No historical catalog is configured for this provider",
		)
	if not source.is_verified:
		raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Historical import requires a verified data source")

	run = sync_source(db, source, IGPHistoricalCatalogConnector(), send_alerts=False)
	record_audit(
		db,
		actor_id=actor.id,
		action="ingestion.historical_backfill",
		entity_type="data_source",
		entity_id=source.id,
		after={
			"run_id": str(run.id), "status": run.status, "catalog_period": "1471-01-01/1959-12-31",
			"records_seen": run.records_seen, "records_inserted": run.records_inserted,
			"records_updated": run.records_updated, "records_duplicated": run.records_duplicated,
			"records_skipped": run.records_skipped,
			"alerts_dispatched": False,
		},
	)
	db.commit()
	return SyncRunResponse(
		id=str(run.id), source_id=str(source.id), started_at=run.started_at,
		finished_at=run.finished_at, status=run.status, records_seen=run.records_seen,
		records_inserted=run.records_inserted, records_updated=run.records_updated,
		records_duplicated=run.records_duplicated, records_skipped=run.records_skipped,
		error_summary=run.error_summary,
	)