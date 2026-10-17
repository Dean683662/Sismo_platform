"""Create immutable, versioned snapshots for analysis and model training."""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.api.v1.schemas import DatasetCreateRequest, DatasetResponse
from backend.core.database import get_db
from backend.core.security import require_csrf, require_permissions
from backend.database.models import Dataset, DataSource, SeismicEvent, User
from backend.ml.preprocessing import prepare_event_dataset


router = APIRouter(prefix="/datasets", tags=["datasets"])


def _dataset_response(dataset: Dataset) -> DatasetResponse:
	return DatasetResponse(
		id=str(dataset.id), name=dataset.name, version=dataset.version,
		query_spec=dataset.query_spec, period_start=dataset.period_start,
		period_end=dataset.period_end, row_count=dataset.row_count,
		quality_report=dataset.quality_report, created_at=dataset.created_at,
	)


@router.post("", response_model=DatasetResponse, status_code=status.HTTP_201_CREATED)
def create_dataset(
	request: DatasetCreateRequest,
	db: Session = Depends(get_db),
	_: None = Depends(require_csrf),
	user: User = Depends(require_permissions("datasets:manage")),
) -> DatasetResponse:
	filters = []
	if request.start_date:
		filters.append(SeismicEvent.occurred_at >= request.start_date)
	if request.end_date:
		filters.append(SeismicEvent.occurred_at <= request.end_date)
	if request.min_magnitude is not None:
		filters.append(SeismicEvent.magnitude >= request.min_magnitude)
	if request.max_magnitude is not None:
		filters.append(SeismicEvent.magnitude <= request.max_magnitude)

	rows = db.execute(
		select(SeismicEvent, DataSource.provider_key)
		.join(DataSource, DataSource.id == SeismicEvent.source_id)
		.where(*filters)
		.order_by(SeismicEvent.occurred_at, SeismicEvent.id)
		.limit(50001)
	).all()
	if len(rows) > 50000:
		raise HTTPException(status_code=413, detail="Narrow the filters to snapshot at most 50,000 events")

	records = [
		{
			"external_id": event.external_id,
			"source_id": str(event.source_id),
			"source_key": source_key,
			"occurred_at": event.occurred_at,
			"latitude": event.latitude,
			"longitude": event.longitude,
			"magnitude": event.magnitude,
			"depth_km": event.depth_km,
		}
		for event, source_key in rows
	]
	prepared = prepare_event_dataset(records)
	source_keys = {
		(record["source_id"], record["external_id"]): record["source_key"]
		for record in records
	}
	snapshot = [
		{
			"external_id": str(row.external_id),
			"source_id": str(row.source_id),
			"source_key": source_keys[(str(row.source_id), str(row.external_id))],
			"occurred_at": row.occurred_at.isoformat(),
			"latitude": float(row.latitude),
			"longitude": float(row.longitude),
			"magnitude": float(row.magnitude),
			"depth_km": float(row.depth_km),
		}
		for row in prepared.itertuples(index=False)
	]
	duplicates = len(records) - len({(record["source_id"], record["external_id"]) for record in records})
	quality_report = {
		"rows_seen": len(records),
		"rows_valid": len(snapshot),
		"rows_removed": len(records) - len(snapshot),
		"duplicates": duplicates,
		"invalid_rows": max(0, len(records) - len(snapshot) - duplicates),
		"missing_by_field": {
			field: sum(record.get(field) is None for record in records)
			for field in ("occurred_at", "latitude", "longitude", "magnitude", "depth_km")
		},
	}
	version = (db.scalar(select(func.max(Dataset.version)).where(Dataset.name == request.name)) or 0) + 1
	period_start = prepared["occurred_at"].min().to_pydatetime() if len(prepared) else None
	period_end = prepared["occurred_at"].max().to_pydatetime() if len(prepared) else None
	dataset = Dataset(
		name=request.name,
		version=version,
		query_spec={
			"start_date": request.start_date.isoformat() if request.start_date else None,
			"end_date": request.end_date.isoformat() if request.end_date else None,
			"min_magnitude": request.min_magnitude,
			"max_magnitude": request.max_magnitude,
			"captured_at": datetime.now(timezone.utc).isoformat(),
		},
		period_start=period_start,
		period_end=period_end,
		row_count=len(snapshot),
		quality_report=quality_report,
		records_json=snapshot,
		created_by=user.id,
	)
	db.add(dataset)
	db.commit()
	db.refresh(dataset)
	return _dataset_response(dataset)


@router.get("", response_model=list[DatasetResponse])
def list_datasets(
	db: Session = Depends(get_db),
	_: User = Depends(require_permissions("analytics:read")),
) -> list[DatasetResponse]:
	datasets = db.scalars(select(Dataset).order_by(Dataset.created_at.desc()).limit(100)).all()
	return [_dataset_response(dataset) for dataset in datasets]


@router.get("/{dataset_id}/quality")
def get_dataset_quality(
	dataset_id: UUID,
	db: Session = Depends(get_db),
	_: User = Depends(require_permissions("analytics:read")),
) -> dict:
	dataset = db.get(Dataset, dataset_id)
	if dataset is None:
		raise HTTPException(status_code=404, detail="Dataset not found")
	return {"dataset_id": str(dataset.id), "name": dataset.name, "version": dataset.version, **dataset.quality_report}