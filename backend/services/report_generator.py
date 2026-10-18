"""Build deterministic report rows from platform records."""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.api.v1.schemas import ReportCreateRequest
from backend.database.models import AlertDelivery, AlertRule, DataSource, Dataset, MLExperiment, SeismicEvent


def _utc(value: datetime | None) -> datetime | None:
	if value is None:
		return None
	return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def generate_report_records(db: Session, request: ReportCreateRequest, generated_at: datetime) -> list[dict]:
	"""Return a bounded, time-cutoff report snapshot for the requested report type."""
	start_date = _utc(request.start_date)
	end_date = _utc(request.end_date)
	if request.report_type == "events":
		query = (
			select(SeismicEvent, DataSource)
			.join(DataSource, DataSource.id == SeismicEvent.source_id)
			.where(SeismicEvent.received_at <= generated_at)
		)
		if start_date:
			query = query.where(SeismicEvent.occurred_at >= start_date)
		if end_date:
			query = query.where(SeismicEvent.occurred_at <= end_date)
		if request.min_magnitude is not None:
			query = query.where(SeismicEvent.magnitude >= request.min_magnitude)
		if request.max_magnitude is not None:
			query = query.where(SeismicEvent.magnitude <= request.max_magnitude)
		if request.source_key:
			query = query.where(DataSource.provider_key == request.source_key)
		rows = db.execute(
			query.order_by(SeismicEvent.occurred_at.desc(), SeismicEvent.id).limit(request.limit)
		).all()
		return [
			{
				"id": str(event.id),
				"external_id": event.external_id,
				"source": source.name,
				"source_key": source.provider_key,
				"source_verified": source.is_verified,
				"occurred_at": event.occurred_at.isoformat(),
				"received_at": event.received_at.isoformat(),
				"latitude": event.latitude,
				"longitude": event.longitude,
				"magnitude": event.magnitude,
				"depth_km": event.depth_km,
				"place": event.place,
				"source_url": event.source_url,
				"review_status": event.review_status,
			}
			for event, source in rows
		]
	if request.report_type == "models":
		query = select(MLExperiment).where(MLExperiment.created_at <= generated_at)
		if start_date:
			query = query.where(MLExperiment.created_at >= start_date)
		if end_date:
			query = query.where(MLExperiment.created_at <= end_date)
		experiments = db.scalars(query.order_by(MLExperiment.created_at.desc(), MLExperiment.id).limit(request.limit)).all()
		return [
			{
				"id": str(item.id),
				"name": item.name,
				"task_type": item.task_type,
				"algorithm": item.algorithm,
				"dataset_id": str(item.dataset_id),
				"metrics": item.metrics,
				"validation_spec": item.validation_spec,
				"status": item.status,
				"limitations": item.limitations,
				"created_at": item.created_at.isoformat(),
			}
			for item in experiments
		]
	if request.report_type == "sources":
		query = select(DataSource).where(DataSource.created_at <= generated_at)
		if start_date:
			query = query.where(DataSource.created_at >= start_date)
		if end_date:
			query = query.where(DataSource.created_at <= end_date)
		sources = db.scalars(query.order_by(DataSource.name).limit(request.limit)).all()
		return [
			{
				"id": str(source.id),
				"provider_key": source.provider_key,
				"name": source.name,
				"organization": source.organization,
				"source_type": source.source_type,
				"status": source.status,
				"is_verified": source.is_verified,
				"base_url": source.base_url,
				"last_sync_at": source.last_sync_at.isoformat() if source.last_sync_at else None,
				"last_success_at": source.last_success_at.isoformat() if source.last_success_at else None,
			}
			for source in sources
		]
	if request.report_type == "quality":
		query = select(Dataset).where(Dataset.created_at <= generated_at)
		if start_date:
			query = query.where(Dataset.created_at >= start_date)
		if end_date:
			query = query.where(Dataset.created_at <= end_date)
		datasets = db.scalars(query.order_by(Dataset.created_at.desc(), Dataset.id).limit(request.limit)).all()
		return [
			{
				"id": str(dataset.id),
				"name": dataset.name,
				"version": dataset.version,
				"row_count": dataset.row_count,
				"period_start": dataset.period_start.isoformat() if dataset.period_start else None,
				"period_end": dataset.period_end.isoformat() if dataset.period_end else None,
				"query_spec": dataset.query_spec,
				"quality_report": dataset.quality_report,
				"created_at": dataset.created_at.isoformat(),
			}
			for dataset in datasets
		]

	query = (
		select(AlertDelivery, AlertRule, SeismicEvent, DataSource)
		.join(AlertRule, AlertRule.id == AlertDelivery.rule_id)
		.join(SeismicEvent, SeismicEvent.id == AlertDelivery.event_id)
		.join(DataSource, DataSource.id == SeismicEvent.source_id)
		.where(AlertDelivery.created_at <= generated_at)
	)
	if start_date:
		query = query.where(AlertDelivery.created_at >= start_date)
	if end_date:
		query = query.where(AlertDelivery.created_at <= end_date)
	rows = db.execute(
		query.order_by(AlertDelivery.created_at.desc(), AlertDelivery.id).limit(request.limit)
	).all()
	return [
		{
			"id": str(delivery.id),
			"rule": rule.name,
			"event_id": str(event.id),
			"source": source.name,
			"magnitude": event.magnitude,
			"place": event.place,
			"status": delivery.status,
			"channel": delivery.channel,
			"message": delivery.message,
			"is_test": delivery.is_test,
			"attempt_count": delivery.attempt_count,
			"last_error": delivery.last_error,
			"created_at": delivery.created_at.isoformat(),
			"delivered_at": delivery.delivered_at.isoformat() if delivery.delivered_at else None,
		}
		for delivery, rule, event, source in rows
	]