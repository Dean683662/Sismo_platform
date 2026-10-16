"""Helpers for writing security-relevant audit records."""

from uuid import UUID

from sqlalchemy.orm import Session

from backend.database.models import AuditLog


def record_audit(
    db: Session,
    *,
    actor_id: UUID | None,
    action: str,
    entity_type: str,
    entity_id: UUID | str | None = None,
    before: dict | None = None,
    after: dict | None = None,
) -> None:
    db.add(
        AuditLog(
            actor_id=actor_id,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else None,
            before_json=before,
            after_json=after,
        )
    )


def user_snapshot(user) -> dict:
    return {
        "full_name": user.full_name,
        "email": user.email,
        "is_active": user.is_active,
        "roles": sorted(role.name for role in user.roles),
    }