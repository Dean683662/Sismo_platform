"""Administrator-only user management and audit query endpoints."""

from uuid import UUID

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, selectinload

from backend.api.v1.endpoints.auth import to_user_response
from backend.api.v1.schemas import (
	AuditLogResponse,
	CreateUserRequest,
	PlatformSettingsResponse,
	PlatformSettingsUpdateRequest,
	RoleResponse,
	UpdateUserRequest,
	UserResponse,
)
from backend.core.database import get_db
from backend.core.security import ROLE_PERMISSIONS, get_current_user, hash_password, require_csrf, require_permissions
from backend.database.models import AlertDelivery, AuditLog, PlatformSetting, ReportRun, Role, User, user_roles
from backend.services.audit_service import record_audit, user_snapshot


router = APIRouter(prefix="/admin", tags=["administration"])
RETENTION_DEFAULTS = {
	"audit_retention_days": 365,
	"alert_history_retention_days": 180,
	"report_retention_days": 365,
}


def _retention_settings(db: Session) -> PlatformSettingsResponse:
	values = dict(RETENTION_DEFAULTS)
	for setting in db.scalars(select(PlatformSetting).where(PlatformSetting.key.in_(values))).all():
		try:
			value = int(setting.value)
		except ValueError as error:
			raise HTTPException(status_code=500, detail=f"Invalid stored setting: {setting.key}") from error
		minimum = 7 if setting.key == "alert_history_retention_days" else 30
		if not minimum <= value <= 3650:
			raise HTTPException(status_code=500, detail=f"Stored setting is outside allowed bounds: {setting.key}")
		values[setting.key] = value
	return PlatformSettingsResponse(**values)


@router.get("/roles", response_model=list[RoleResponse])
def list_roles(
	db: Session = Depends(get_db),
	_: User = Depends(require_permissions("users:read")),
) -> list[RoleResponse]:
	roles = db.scalars(select(Role).order_by(Role.name)).all()
	return [
		RoleResponse(name=role.name, description=role.description, permissions=sorted(ROLE_PERMISSIONS[role.name]))
		for role in roles
	]


@router.get("/users", response_model=list[UserResponse])
def list_users(
	db: Session = Depends(get_db),
	_: User = Depends(require_permissions("users:read")),
) -> list[UserResponse]:
	users = db.scalars(select(User).options(selectinload(User.roles)).order_by(User.created_at.desc())).all()
	return [to_user_response(user) for user in users]


@router.post(
	"/users",
	response_model=UserResponse,
	status_code=status.HTTP_201_CREATED,
	dependencies=[Depends(require_csrf)],
)
def create_user(
	payload: CreateUserRequest,
	db: Session = Depends(get_db),
	actor: User = Depends(require_permissions("users:write")),
) -> UserResponse:
	email = str(payload.email).lower()
	if db.scalar(select(User.id).where(User.email == email)):
		raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email is already registered")

	roles = list(db.scalars(select(Role).where(Role.name.in_(payload.roles))).all())
	if len(roles) != len(set(payload.roles)):
		raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unknown role")

	user = User(
		full_name=payload.full_name.strip(),
		email=email,
		password_hash=hash_password(payload.password),
		roles=roles,
	)
	db.add(user)
	db.flush()
	record_audit(
		db,
		actor_id=actor.id,
		action="admin.user_created",
		entity_type="user",
		entity_id=user.id,
		after=user_snapshot(user),
	)
	db.commit()
	db.refresh(user)
	return to_user_response(user)


@router.patch(
	"/users/{user_id}",
	response_model=UserResponse,
	dependencies=[Depends(require_csrf)],
)
def update_user(
	user_id: UUID,
	payload: UpdateUserRequest,
	db: Session = Depends(get_db),
	actor: User = Depends(require_permissions("users:write")),
) -> UserResponse:
	user = db.scalar(select(User).options(selectinload(User.roles)).where(User.id == user_id))
	if user is None:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
	if user.id == actor.id and payload.is_active is False:
		raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="You cannot deactivate your own account")

	before = user_snapshot(user)
	current_roles = {role.name for role in user.roles}
	next_roles = set(payload.roles) if payload.roles is not None else current_roles
	next_active = payload.is_active if payload.is_active is not None else user.is_active

	removes_active_admin = (
		user.is_active
		and "administrator" in current_roles
		and (not next_active or "administrator" not in next_roles)
	)
	if removes_active_admin:
		active_admin_count = db.scalar(
			select(func.count(User.id))
			.join(user_roles, user_roles.c.user_id == User.id)
			.where(User.is_active.is_(True), user_roles.c.role_id == "administrator")
		)
		if active_admin_count <= 1:
			raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="At least one active administrator is required")

	if payload.roles is not None:
		roles = list(db.scalars(select(Role).where(Role.name.in_(payload.roles))).all())
		if len(roles) != len(set(payload.roles)):
			raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unknown role")
		user.roles = roles
	if payload.is_active is not None:
		user.is_active = payload.is_active

	record_audit(
		db,
		actor_id=actor.id,
		action="admin.user_updated",
		entity_type="user",
		entity_id=user.id,
		before=before,
		after=user_snapshot(user),
	)
	db.commit()
	return to_user_response(user)


@router.get("/audit-logs", response_model=list[AuditLogResponse])
def list_audit_logs(
	limit: int = Query(default=100, ge=1, le=500),
	db: Session = Depends(get_db),
	_: User = Depends(require_permissions("audit:read")),
) -> list[AuditLogResponse]:
	entries = db.scalars(select(AuditLog).order_by(AuditLog.occurred_at.desc()).limit(limit)).all()
	return [
		AuditLogResponse(
			id=str(entry.id),
			actor_id=str(entry.actor_id) if entry.actor_id else None,
			action=entry.action,
			entity_type=entry.entity_type,
			entity_id=entry.entity_id,
			before_json=entry.before_json,
			after_json=entry.after_json,
			occurred_at=entry.occurred_at.isoformat(),
		)
		for entry in entries
	]


@router.get("/settings", response_model=PlatformSettingsResponse)
def get_platform_settings(
	db: Session = Depends(get_db),
	_: User = Depends(require_permissions("settings:manage")),
) -> PlatformSettingsResponse:
	return _retention_settings(db)


@router.patch(
	"/settings",
	response_model=PlatformSettingsResponse,
	dependencies=[Depends(require_csrf)],
)
def update_platform_settings(
	payload: PlatformSettingsUpdateRequest,
	db: Session = Depends(get_db),
	actor: User = Depends(require_permissions("settings:manage")),
) -> PlatformSettingsResponse:
	before = _retention_settings(db).model_dump()
	for key, value in payload.model_dump().items():
		setting = db.get(PlatformSetting, key)
		if setting is None:
			db.add(PlatformSetting(key=key, value=str(value)))
		else:
			setting.value = str(value)
			setting.updated_at = datetime.now(timezone.utc)
	record_audit(
		db,
		actor_id=actor.id,
		action="admin.settings_updated",
		entity_type="platform_settings",
		after=payload.model_dump(),
		before=before,
	)
	db.commit()
	return _retention_settings(db)


@router.post("/retention/run", dependencies=[Depends(require_csrf)])
def run_retention_cleanup(
	db: Session = Depends(get_db),
	actor: User = Depends(require_permissions("settings:manage")),
) -> dict[str, int | str]:
	settings = _retention_settings(db)
	now = datetime.now(timezone.utc)
	audit_cutoff = now - timedelta(days=settings.audit_retention_days)
	alert_cutoff = now - timedelta(days=settings.alert_history_retention_days)
	report_cutoff = now - timedelta(days=settings.report_retention_days)
	deleted_audit = db.scalar(
		select(func.count()).select_from(AuditLog).where(AuditLog.occurred_at < audit_cutoff)
	) or 0
	deleted_deliveries = db.scalar(
		select(func.count())
		.select_from(AlertDelivery)
		.where(
			AlertDelivery.created_at < alert_cutoff,
			AlertDelivery.status.in_(("delivered", "rejected", "failed")),
		)
	) or 0
	deleted_reports = db.scalar(
		select(func.count()).select_from(ReportRun).where(ReportRun.created_at < report_cutoff)
	) or 0
	db.execute(delete(AuditLog).where(AuditLog.occurred_at < audit_cutoff))
	db.execute(
		delete(AlertDelivery).where(
			AlertDelivery.created_at < alert_cutoff,
			AlertDelivery.status.in_(("delivered", "rejected", "failed")),
		)
	)
	db.execute(delete(ReportRun).where(ReportRun.created_at < report_cutoff))
	record_audit(
		db,
		actor_id=actor.id,
		action="admin.retention_executed",
		entity_type="retention",
		after={
			"audit_retention_days": settings.audit_retention_days,
			"alert_history_retention_days": settings.alert_history_retention_days,
			"report_retention_days": settings.report_retention_days,
			"deleted_audit_logs": deleted_audit,
			"deleted_alert_deliveries": deleted_deliveries,
			"deleted_report_snapshots": deleted_reports,
		},
	)
	db.commit()
	return {
		"status": "completed",
		"deleted_audit_logs": deleted_audit,
		"deleted_alert_deliveries": deleted_deliveries,
		"deleted_report_snapshots": deleted_reports,
	}