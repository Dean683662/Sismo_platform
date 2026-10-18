"""Evaluate alert rules and persist auditable in-app deliveries."""

import logging
import time
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.database.models import AlertDelivery, AlertRule, DataSource, SeismicEvent
from backend.services.alert_dispatcher import send_alert_webhook
from backend.services.audit_service import record_audit


logger = logging.getLogger(__name__)


def _message(rule: AlertRule, event: SeismicEvent, source: DataSource) -> str:
    return rule.template.format_map(
        {
            "magnitude": f"{event.magnitude:.1f}",
            "place": event.place,
            "occurred_at": event.occurred_at.isoformat(),
            "source_name": source.name,
        }
    )


def _matches(rule: AlertRule, event: SeismicEvent, source: DataSource) -> bool:
    if not rule.is_enabled or not source.is_verified or source.status != "active":
        return False
    if event.magnitude < rule.min_magnitude:
        return False
    if rule.min_depth_km is not None and event.depth_km < rule.min_depth_km:
        return False
    if rule.source_ids and str(source.id) not in rule.source_ids:
        return False
    if rule.region_bounds:
        bounds = rule.region_bounds
        if not (
            bounds["min_latitude"] <= event.latitude <= bounds["max_latitude"]
            and bounds["min_longitude"] <= event.longitude <= bounds["max_longitude"]
        ):
            return False
    return True


def _create_delivery(
    db: Session,
    rule: AlertRule,
    event: SeismicEvent,
    source: DataSource,
    *,
    is_test: bool = False,
) -> AlertDelivery | None:
    deduplication_key = (
        f"test:{uuid4()}" if is_test else f"event:{rule.id}:{event.source_id}:{event.external_id}"
    )
    delivery = AlertDelivery(
        rule_id=rule.id,
        event_id=event.id,
        status=(
            "pending_approval"
            if rule.requires_approval and not is_test
            else "queued"
            if rule.channel == "webhook"
            else "delivered"
        ),
        channel=rule.channel,
        message=_message(rule, event, source),
        deduplication_key=deduplication_key,
        is_test=is_test,
        attempt_count=0 if rule.channel == "webhook" or rule.requires_approval else 1,
        delivered_at=(
            datetime.now(timezone.utc)
            if rule.channel == "in_app" and (not rule.requires_approval or is_test)
            else None
        ),
    )
    try:
        with db.begin_nested():
            db.add(delivery)
            db.flush()
    except IntegrityError:
        existing_id = db.scalar(
            select(AlertDelivery.id).where(AlertDelivery.deduplication_key == deduplication_key)
        )
        if existing_id is None:
            raise
        return None
    return delivery


def evaluate_event_alerts(db: Session, event: SeismicEvent, source: DataSource) -> int:
    """Create one delivery at most for each matching rule and source event."""
    if not source.is_verified:
        return 0
    rules = db.scalars(select(AlertRule).where(AlertRule.is_enabled.is_(True))).all()
    created = 0
    for rule in rules:
        if _matches(rule, event, source):
            delivery = _create_delivery(db, rule, event, source)
            if delivery is not None:
                record_audit(
                    db,
                    actor_id=None,
                    action="alerts.delivery_created",
                    entity_type="alert_delivery",
                    entity_id=delivery.id,
                    after={"rule_id": str(rule.id), "event_id": str(event.id), "status": delivery.status, "channel": delivery.channel},
                )
                created += 1
    return created


def create_test_delivery(db: Session, rule: AlertRule, event: SeismicEvent, source: DataSource) -> AlertDelivery:
    delivery = _create_delivery(db, rule, event, source, is_test=True)
    if delivery is None:
        raise RuntimeError("A test delivery was unexpectedly deduplicated")
    return delivery


def _deliver_webhook(
    delivery: AlertDelivery,
    rule: AlertRule,
    event: SeismicEvent,
    source: DataSource,
    *,
    max_new_attempts: int,
) -> None:
    if settings.alert_webhook_url is None:
        delivery.attempt_count += 1
        delivery.status = "failed"
        delivery.last_error = "webhook_not_configured"
        logger.warning("Alert webhook delivery failed: delivery_id=%s reason=webhook_not_configured", delivery.id)
        return
    payload = {
        "delivery_id": str(delivery.id),
        "deduplication_key": delivery.deduplication_key,
        "rule": {"id": str(rule.id), "name": rule.name},
        "event": {
            "id": str(event.id),
            "external_id": event.external_id,
            "magnitude": event.magnitude,
            "depth_km": event.depth_km,
            "place": event.place,
            "occurred_at": event.occurred_at.isoformat(),
            "source": source.name,
            "source_url": event.source_url,
        },
        "message": delivery.message,
        "is_test": delivery.is_test,
    }
    last_error: str | None = None
    attempts = min(max_new_attempts, max(0, 3 - delivery.attempt_count))
    for attempt in range(attempts):
        delivery.attempt_count += 1
        last_error = send_alert_webhook(payload, delivery.deduplication_key)
        if last_error is None:
            delivery.status = "delivered"
            delivery.last_error = None
            delivery.delivered_at = datetime.now(timezone.utc)
            return
        if attempt + 1 < attempts:
            time.sleep(0.2 * (attempt + 1))
    delivery.status = "failed"
    delivery.last_error = last_error or "maximum_attempts_reached"
    logger.warning(
        "Alert webhook delivery failed: delivery_id=%s attempts=%s reason=%s",
        delivery.id,
        delivery.attempt_count,
        delivery.last_error,
    )


def deliver_approved_alert(
    delivery: AlertDelivery,
    rule: AlertRule,
    event: SeismicEvent,
    source: DataSource,
    *,
    max_new_attempts: int = 2,
) -> None:
    if delivery.channel == "webhook":
        _deliver_webhook(delivery, rule, event, source, max_new_attempts=max_new_attempts)
        return
    delivery.status = "delivered"
    delivery.attempt_count += 1
    delivery.last_error = None
    delivery.delivered_at = datetime.now(timezone.utc)


def retry_failed_delivery(
    delivery: AlertDelivery,
    rule: AlertRule,
    event: SeismicEvent,
    source: DataSource,
) -> None:
    deliver_approved_alert(delivery, rule, event, source, max_new_attempts=1)


def dispatch_queued_deliveries(db: Session, *, limit: int = 10) -> int:
    rows = db.execute(
        select(AlertDelivery, AlertRule, SeismicEvent, DataSource)
        .join(AlertRule, AlertRule.id == AlertDelivery.rule_id)
        .join(SeismicEvent, SeismicEvent.id == AlertDelivery.event_id)
        .join(DataSource, DataSource.id == SeismicEvent.source_id)
        .where(AlertDelivery.status == "queued", AlertDelivery.attempt_count < 3)
        .order_by(AlertDelivery.created_at, AlertDelivery.id)
        .limit(limit)
    ).all()
    for delivery, rule, event, source in rows:
        deliver_approved_alert(delivery, rule, event, source, max_new_attempts=1)
        record_audit(
            db,
            actor_id=None,
            action="alerts.delivery_attempted",
            entity_type="alert_delivery",
            entity_id=delivery.id,
            after={"attempt_count": delivery.attempt_count, "status": delivery.status, "channel": delivery.channel},
        )
    if rows:
        db.commit()
    return len(rows)
