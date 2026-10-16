"""Search and retrieve normalized seismic events."""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.api.v1.schemas import EventPageResponse, EventResponse
from backend.core.database import get_db
from backend.core.security import require_permissions
from backend.database.models import DataSource, SeismicEvent, User


router = APIRouter(prefix="/events", tags=["events"])


def _as_utc(value: datetime | None) -> datetime | None:
	if value is None:
		return None
	if value.tzinfo is None:
		return value.replace(tzinfo=timezone.utc)
	return value.astimezone(timezone.utc)


def _event_response(event: SeismicEvent, source_key: str) -> EventResponse:
	return EventResponse(
		id=str(event.id), external_id=event.external_id, source_key=source_key,
		occurred_at=event.occurred_at, latitude=event.latitude, longitude=event.longitude,
		magnitude=event.magnitude, magnitude_type=event.magnitude_type, depth_km=event.depth_km,
		place=event.place, source_url=event.source_url, received_at=event.received_at,
		review_status=event.review_status,
	)


@router.get("", response_model=EventPageResponse)
def list_events(
	start_date: datetime | None = None,
	end_date: datetime | None = None,
	min_magnitude: float | None = Query(default=None, ge=0, le=10),
	max_magnitude: float | None = Query(default=None, ge=0, le=10),
	source_key: str | None = Query(default=None, max_length=40),
	limit: int = Query(default=50, ge=1, le=200),
	offset: int = Query(default=0, ge=0),
	db: Session = Depends(get_db),
	_: User = Depends(require_permissions("events:read")),
) -> EventPageResponse:
	start_date = _as_utc(start_date)
	end_date = _as_utc(end_date)
	if start_date and end_date and start_date > end_date:
		raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="start_date must be before end_date")
	if min_magnitude is not None and max_magnitude is not None and min_magnitude > max_magnitude:
		raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="min_magnitude must not exceed max_magnitude")

	filters = []
	if start_date:
		filters.append(SeismicEvent.occurred_at >= start_date)
	if end_date:
		filters.append(SeismicEvent.occurred_at <= end_date)
	if min_magnitude is not None:
		filters.append(SeismicEvent.magnitude >= min_magnitude)
	if max_magnitude is not None:
		filters.append(SeismicEvent.magnitude <= max_magnitude)
	if source_key:
		filters.append(DataSource.provider_key == source_key)

	query = select(SeismicEvent, DataSource.provider_key).join(DataSource, DataSource.id == SeismicEvent.source_id).where(*filters)
	total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
	rows = db.execute(query.order_by(SeismicEvent.occurred_at.desc(), SeismicEvent.id).offset(offset).limit(limit)).all()
	return EventPageResponse(items=[_event_response(event, key) for event, key in rows], total=total, limit=limit, offset=offset)


@router.get("/{event_id}", response_model=EventResponse)
def get_event(
	event_id: UUID,
	db: Session = Depends(get_db),
	_: User = Depends(require_permissions("events:read")),
) -> EventResponse:
	row = db.execute(
		select(SeismicEvent, DataSource.provider_key)
		.join(DataSource, DataSource.id == SeismicEvent.source_id)
		.where(SeismicEvent.id == event_id)
	).first()
	if row is None:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
	return _event_response(*row)