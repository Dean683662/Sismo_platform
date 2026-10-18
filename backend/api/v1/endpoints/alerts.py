"""Manage alert rules, approvals, and auditable in-app delivery history."""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.api.v1.schemas import (
	AlertDeliveryResponse,
	AlertRuleCreateRequest,
	AlertRuleResponse,
	AlertRuleUpdateRequest,
	AlertTestRequest,
)
from backend.core.config import settings
from backend.core.database import get_db
from backend.core.security import require_csrf, require_permissions
from backend.database.models import AlertDelivery, AlertRule, DataSource, SeismicEvent, User
from backend.services.alert_service import (
	create_test_delivery,
	deliver_approved_alert,
	retry_failed_delivery,
)
from backend.services.audit_service import record_audit


router = APIRouter(prefix="/alerts", tags=["alerts"])


def _rule_response(rule: AlertRule) -> AlertRuleResponse:
	return AlertRuleResponse(
		id=str(rule.id),
		name=rule.name,
		is_enabled=rule.is_enabled,
		min_magnitude=rule.min_magnitude,
		min_depth_km=rule.min_depth_km,
		region_bounds=rule.region_bounds,
		source_ids=rule.source_ids,
		channel=rule.channel,
		requires_approval=rule.requires_approval,
		template=rule.template,
		created_at=rule.created_at,
		updated_at=rule.updated_at,
	)


def _delivery_response(
	delivery: AlertDelivery,
	rule: AlertRule,
	event: SeismicEvent,
	source: DataSource,
) -> AlertDeliveryResponse:
	return AlertDeliveryResponse(
		id=str(delivery.id),
		rule_id=str(rule.id),
		rule_name=rule.name,
		event_id=str(event.id),
		source_name=source.name,
		source_url=event.source_url,
		event_magnitude=event.magnitude,
		event_place=event.place,
		event_occurred_at=event.occurred_at,
		status=delivery.status,
		channel=delivery.channel,
		message=delivery.message,
		is_test=delivery.is_test,
		attempt_count=delivery.attempt_count,
		last_error=delivery.last_error,
		created_at=delivery.created_at,
		delivered_at=delivery.delivered_at,
		reviewed_at=delivery.reviewed_at,
	)


def _get_delivery(db: Session, delivery_id: UUID) -> tuple[AlertDelivery, AlertRule, SeismicEvent, DataSource]:
	row = db.execute(
		select(AlertDelivery, AlertRule, SeismicEvent, DataSource)
		.join(AlertRule, AlertRule.id == AlertDelivery.rule_id)
		.join(SeismicEvent, SeismicEvent.id == AlertDelivery.event_id)
		.join(DataSource, DataSource.id == SeismicEvent.source_id)
		.where(AlertDelivery.id == delivery_id)
	).first()
	if row is None:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert delivery not found")
	return row


def _validated_source_ids(db: Session, source_ids: list[str]) -> list[str]:
	if not source_ids:
		return []
	try:
		parsed = list({UUID(value) for value in source_ids})
	except ValueError:
		raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid source id") from None
	sources = db.scalars(
		select(DataSource).where(DataSource.id.in_(parsed), DataSource.is_verified.is_(True))
	).all()
	if len(sources) != len(parsed):
		raise HTTPException(
			status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
			detail="Alert rules can only use verified data sources",
		)
	return [str(source.id) for source in sources]


@router.get("/rules", response_model=list[AlertRuleResponse])
def list_alert_rules(
	db: Session = Depends(get_db),
	_: User = Depends(require_permissions("alerts:read")),
) -> list[AlertRuleResponse]:
	rules = db.scalars(select(AlertRule).order_by(AlertRule.created_at.desc())).all()
	return [_rule_response(rule) for rule in rules]


@router.post(
	"/rules",
	response_model=AlertRuleResponse,
	status_code=status.HTTP_201_CREATED,
	dependencies=[Depends(require_csrf)],
)
def create_alert_rule(
	payload: AlertRuleCreateRequest,
	db: Session = Depends(get_db),
	actor: User = Depends(require_permissions("alerts:manage")),
) -> AlertRuleResponse:
	if payload.channel == "webhook" and settings.alert_webhook_url is None:
		raise HTTPException(
			status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
			detail="Configure ALERT_WEBHOOK_URL on the API before selecting webhook delivery",
		)
	values = payload.model_dump()
	values["source_ids"] = _validated_source_ids(db, payload.source_ids)
	rule = AlertRule(**values, created_by=actor.id)
	db.add(rule)
	db.flush()
	record_audit(
		db,
		actor_id=actor.id,
		action="alerts.rule_created",
		entity_type="alert_rule",
		entity_id=rule.id,
		after={"name": rule.name, "min_magnitude": rule.min_magnitude, "source_ids": rule.source_ids},
	)
	db.commit()
	db.refresh(rule)
	return _rule_response(rule)


@router.patch(
	"/rules/{rule_id}",
	response_model=AlertRuleResponse,
	dependencies=[Depends(require_csrf)],
)
def update_alert_rule(
	rule_id: UUID,
	payload: AlertRuleUpdateRequest,
	db: Session = Depends(get_db),
	actor: User = Depends(require_permissions("alerts:manage")),
) -> AlertRuleResponse:
	if payload.channel == "webhook" and settings.alert_webhook_url is None:
		raise HTTPException(
			status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
			detail="Configure ALERT_WEBHOOK_URL on the API before selecting webhook delivery",
		)
	rule = db.get(AlertRule, rule_id)
	if rule is None:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert rule not found")
	before = {
		"name": rule.name,
		"is_enabled": rule.is_enabled,
		"min_magnitude": rule.min_magnitude,
		"min_depth_km": rule.min_depth_km,
		"region_bounds": rule.region_bounds,
		"source_ids": rule.source_ids,
		"channel": rule.channel,
		"requires_approval": rule.requires_approval,
		"template": rule.template,
	}
	changes = payload.model_dump(exclude_unset=True)
	if "source_ids" in changes and changes["source_ids"] is not None:
		changes["source_ids"] = _validated_source_ids(db, changes["source_ids"])
	for field, value in changes.items():
		setattr(rule, field, value)
	rule.updated_at = datetime.now(timezone.utc)
	record_audit(
		db,
		actor_id=actor.id,
		action="alerts.rule_updated",
		entity_type="alert_rule",
		entity_id=rule.id,
		before=before,
		after={**before, **changes},
	)
	db.commit()
	db.refresh(rule)
	return _rule_response(rule)


@router.post(
	"/rules/{rule_id}/test",
	response_model=AlertDeliveryResponse,
	status_code=status.HTTP_201_CREATED,
	dependencies=[Depends(require_csrf)],
)
def send_test_alert(
	rule_id: UUID,
	payload: AlertTestRequest,
	db: Session = Depends(get_db),
	actor: User = Depends(require_permissions("alerts:manage")),
) -> AlertDeliveryResponse:
	rule = db.get(AlertRule, rule_id)
	if rule is None:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert rule not found")
	sources_query = select(DataSource).where(
		DataSource.is_verified.is_(True),
		DataSource.status == "active",
	)
	if payload.source_id:
		try:
			source_id = UUID(payload.source_id)
		except ValueError:
			raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid source id") from None
		if rule.source_ids and str(source_id) not in rule.source_ids:
			raise HTTPException(
				status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
				detail="The test source is not selected by this alert rule",
			)
		sources_query = sources_query.where(DataSource.id == source_id)
	elif rule.source_ids:
		sources_query = sources_query.where(DataSource.id.in_([UUID(value) for value in rule.source_ids]))
	source = db.scalar(sources_query.order_by(DataSource.name).limit(1))
	if source is None:
		raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No active verified source is available")
	event = db.scalar(
		select(SeismicEvent)
		.where(SeismicEvent.source_id == source.id)
		.order_by(SeismicEvent.occurred_at.desc())
		.limit(1)
	)
	if event is None:
		raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="The verified source has no event to test")
	delivery = create_test_delivery(db, rule, event, source)
	record_audit(
		db,
		actor_id=actor.id,
		action="alerts.test_sent",
		entity_type="alert_delivery",
		entity_id=delivery.id,
		after={"rule_id": str(rule.id), "event_id": str(event.id), "status": delivery.status},
	)
	db.commit()
	if delivery.status == "queued":
		deliver_approved_alert(delivery, rule, event, source)
		record_audit(
			db,
			actor_id=actor.id,
			action="alerts.delivery_attempted",
			entity_type="alert_delivery",
			entity_id=delivery.id,
			after={"attempt_count": delivery.attempt_count, "status": delivery.status, "channel": delivery.channel},
		)
		db.commit()
	db.refresh(delivery)
	return _delivery_response(delivery, rule, event, source)


@router.get("/deliveries", response_model=list[AlertDeliveryResponse])
def list_alert_deliveries(
	rule_id: UUID | None = None,
	delivery_status: str | None = Query(default=None, alias="status", pattern="^(queued|pending_approval|delivered|rejected|failed)$"),
	limit: int = Query(default=100, ge=1, le=500),
	offset: int = Query(default=0, ge=0),
	db: Session = Depends(get_db),
	_: User = Depends(require_permissions("alerts:read")),
) -> list[AlertDeliveryResponse]:
	query = (
		select(AlertDelivery, AlertRule, SeismicEvent, DataSource)
		.join(AlertRule, AlertRule.id == AlertDelivery.rule_id)
		.join(SeismicEvent, SeismicEvent.id == AlertDelivery.event_id)
		.join(DataSource, DataSource.id == SeismicEvent.source_id)
	)
	if rule_id is not None:
		query = query.where(AlertDelivery.rule_id == rule_id)
	if delivery_status is not None:
		query = query.where(AlertDelivery.status == delivery_status)
	rows = db.execute(
		query.order_by(AlertDelivery.created_at.desc(), AlertDelivery.id).offset(offset).limit(limit)
	).all()
	return [_delivery_response(*row) for row in rows]


@router.post("/deliveries/{delivery_id}/approve", response_model=AlertDeliveryResponse, dependencies=[Depends(require_csrf)])
def approve_alert_delivery(
	delivery_id: UUID,
	db: Session = Depends(get_db),
	actor: User = Depends(require_permissions("alerts:manage")),
) -> AlertDeliveryResponse:
	delivery, rule, event, source = _get_delivery(db, delivery_id)
	if delivery.status != "pending_approval":
		raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Alert is not awaiting approval")
	if delivery.channel == "webhook":
		delivery.status = "queued"
	else:
		deliver_approved_alert(delivery, rule, event, source)
	delivery.reviewed_by = actor.id
	delivery.reviewed_at = datetime.now(timezone.utc)
	record_audit(
		db,
		actor_id=actor.id,
		action="alerts.delivery_approved",
		entity_type="alert_delivery",
		entity_id=delivery.id,
		after={"rule_id": str(rule.id), "event_id": str(event.id), "status": delivery.status},
	)
	db.commit()
	if delivery.status == "queued":
		deliver_approved_alert(delivery, rule, event, source)
		record_audit(
			db,
			actor_id=actor.id,
			action="alerts.delivery_attempted",
			entity_type="alert_delivery",
			entity_id=delivery.id,
			after={"attempt_count": delivery.attempt_count, "status": delivery.status, "channel": delivery.channel},
		)
		db.commit()
	db.refresh(delivery)
	return _delivery_response(delivery, rule, event, source)


@router.post("/deliveries/{delivery_id}/reject", response_model=AlertDeliveryResponse, dependencies=[Depends(require_csrf)])
def reject_alert_delivery(
	delivery_id: UUID,
	db: Session = Depends(get_db),
	actor: User = Depends(require_permissions("alerts:manage")),
) -> AlertDeliveryResponse:
	delivery, rule, event, source = _get_delivery(db, delivery_id)
	if delivery.status != "pending_approval":
		raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Alert is not awaiting approval")
	delivery.status = "rejected"
	delivery.reviewed_by = actor.id
	delivery.reviewed_at = datetime.now(timezone.utc)
	record_audit(
		db,
		actor_id=actor.id,
		action="alerts.delivery_rejected",
		entity_type="alert_delivery",
		entity_id=delivery.id,
		after={"rule_id": str(rule.id), "event_id": str(event.id), "status": delivery.status},
	)
	db.commit()
	db.refresh(delivery)
	return _delivery_response(delivery, rule, event, source)


@router.post("/deliveries/{delivery_id}/retry", response_model=AlertDeliveryResponse, dependencies=[Depends(require_csrf)])
def retry_alert_delivery(
	delivery_id: UUID,
	db: Session = Depends(get_db),
	actor: User = Depends(require_permissions("alerts:manage")),
) -> AlertDeliveryResponse:
	delivery, rule, event, source = _get_delivery(db, delivery_id)
	if delivery.status != "failed":
		raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only failed deliveries can be retried")
	if delivery.attempt_count >= 3:
		raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Maximum delivery attempts reached")
	delivery.status = "queued"
	db.commit()
	retry_failed_delivery(delivery, rule, event, source)
	record_audit(
		db,
		actor_id=actor.id,
		action="alerts.delivery_retried",
		entity_type="alert_delivery",
		entity_id=delivery.id,
		after={"attempt_count": delivery.attempt_count, "status": delivery.status},
	)
	db.commit()
	db.refresh(delivery)
	return _delivery_response(delivery, rule, event, source)