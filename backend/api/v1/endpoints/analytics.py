"""Dashboard, temporal analysis, and geographic event data."""

from collections import Counter
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.api.v1.schemas import DashboardSummaryResponse, TimeSeriesPoint, TimeSeriesResponse
from backend.core.database import get_db
from backend.core.security import require_permissions
from backend.database.models import DataSource, SeismicEvent, User


router = APIRouter(tags=["analytics"])


def _event_filters(
	start_date: datetime | None,
	end_date: datetime | None,
	min_magnitude: float | None,
	max_magnitude: float | None,
) -> list:
	if start_date and start_date.tzinfo is None:
		start_date = start_date.replace(tzinfo=timezone.utc)
	if end_date and end_date.tzinfo is None:
		end_date = end_date.replace(tzinfo=timezone.utc)
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
	return filters


@router.get("/dashboard/summary", response_model=DashboardSummaryResponse)
def dashboard_summary(
	db: Session = Depends(get_db),
	_: User = Depends(require_permissions("analytics:read")),
) -> DashboardSummaryResponse:
	now = datetime.now(timezone.utc)
	return DashboardSummaryResponse(
		total_events=db.scalar(select(func.count()).select_from(SeismicEvent)) or 0,
		events_last_24h=db.scalar(
			select(func.count()).select_from(SeismicEvent).where(SeismicEvent.occurred_at >= now - timedelta(hours=24))
		) or 0,
		latest_event_at=db.scalar(select(func.max(SeismicEvent.occurred_at))),
		active_sources=db.scalar(select(func.count()).select_from(DataSource).where(DataSource.status == "active")) or 0,
		total_sources=db.scalar(select(func.count()).select_from(DataSource)) or 0,
		last_sync_at=db.scalar(select(func.max(DataSource.last_sync_at))),
	)


@router.get("/analytics/timeseries", response_model=TimeSeriesResponse)
def event_timeseries(
	start_date: datetime | None = None,
	end_date: datetime | None = None,
	min_magnitude: float | None = Query(default=None, ge=0, le=10),
	max_magnitude: float | None = Query(default=None, ge=0, le=10),
	group_by: str = Query(default="day", pattern="^(day|week)$"),
	db: Session = Depends(get_db),
	_: User = Depends(require_permissions("analytics:read")),
) -> TimeSeriesResponse:
	if start_date is None:
		start_date = datetime.now(timezone.utc) - timedelta(days=30)
	if end_date is None:
		end_date = datetime.now(timezone.utc)
	filters = _event_filters(start_date, end_date, min_magnitude, max_magnitude)
	rows = db.scalars(
		select(SeismicEvent.occurred_at)
		.where(*filters)
		.order_by(SeismicEvent.occurred_at)
		.limit(50001)
	).all()
	if len(rows) > 50000:
		raise HTTPException(status_code=413, detail="Narrow the date range to analyze at most 50,000 events")

	counts: Counter[datetime] = Counter()
	for timestamp in rows:
		if timestamp.tzinfo is None:
			timestamp = timestamp.replace(tzinfo=timezone.utc)
		if group_by == "week":
			bucket_date = (timestamp - timedelta(days=timestamp.weekday())).date()
		else:
			bucket_date = timestamp.date()
		bucket = datetime.combine(bucket_date, datetime.min.time(), tzinfo=timezone.utc)
		counts[bucket] += 1

	return TimeSeriesResponse(
		items=[TimeSeriesPoint(period_start=period, event_count=count) for period, count in sorted(counts.items())],
		total_events=len(rows),
		period_start=start_date,
		period_end=end_date,
		group_by=group_by,
	)


@router.get("/events/geojson")
def event_geojson(
	start_date: datetime | None = None,
	end_date: datetime | None = None,
	min_magnitude: float | None = Query(default=None, ge=0, le=10),
	max_magnitude: float | None = Query(default=None, ge=0, le=10),
	min_latitude: float | None = Query(default=None, ge=-90, le=90),
	max_latitude: float | None = Query(default=None, ge=-90, le=90),
	min_longitude: float | None = Query(default=None, ge=-180, le=180),
	max_longitude: float | None = Query(default=None, ge=-180, le=180),
	limit: int = Query(default=2000, ge=1, le=5000),
	db: Session = Depends(get_db),
	_: User = Depends(require_permissions("events:read")),
) -> dict:
	filters = _event_filters(start_date, end_date, min_magnitude, max_magnitude)
	bounds = (min_latitude, max_latitude, min_longitude, max_longitude)
	if any(value is not None for value in bounds) and not all(value is not None for value in bounds):
		raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Provide all four geographic bounds")
	if all(value is not None for value in bounds):
		if min_latitude >= max_latitude or min_longitude >= max_longitude:
			raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Geographic bounds are invalid")
		filters.extend(
			(
				SeismicEvent.latitude >= min_latitude,
				SeismicEvent.latitude <= max_latitude,
				SeismicEvent.longitude >= min_longitude,
				SeismicEvent.longitude <= max_longitude,
			)
		)
	rows = db.execute(
		select(SeismicEvent, DataSource.provider_key)
		.join(DataSource, DataSource.id == SeismicEvent.source_id)
		.where(*filters)
		.order_by(SeismicEvent.occurred_at.desc())
		.limit(limit)
	).all()
	return {
		"type": "FeatureCollection",
		"features": [
			{
				"type": "Feature",
				"id": str(event.id),
				"geometry": {"type": "Point", "coordinates": [event.longitude, event.latitude]},
				"properties": {
					"magnitude": event.magnitude,
					"depth_km": event.depth_km,
					"occurred_at": event.occurred_at.isoformat(),
					"place": event.place,
					"source_key": source_key,
					"source_url": event.source_url,
				},
			}
			for event, source_key in rows
		],
	}