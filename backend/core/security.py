"""Password hashing, signed sessions, CSRF checks, and RBAC dependencies."""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Callable
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, Request, status
from pwdlib import PasswordHash
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.core.database import get_db
from backend.database.models import User


password_hasher = PasswordHash.recommended()
dummy_password_hash = password_hasher.hash("invalid-password-used-for-timing-equalization")

ROLE_PERMISSIONS: dict[str, set[str]] = {
	"administrator": {
		"users:read", "users:write", "audit:read", "settings:manage", "events:read",
		"analytics:read", "datasets:manage", "models:read", "models:manage", "estimates:read", "reports:read", "alerts:read",
		"alerts:manage", "sources:read", "sources:manage",
	},
	"analyst": {"events:read", "analytics:read", "datasets:manage", "models:read", "models:manage", "estimates:read", "reports:read"},
	"alert_operator": {"events:read", "alerts:read", "alerts:manage"},
	"auditor": {"events:read", "reports:read", "audit:read"},
	"read_only": {"events:read", "analytics:read", "reports:read"},
}


def hash_password(password: str) -> str:
	return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
	return password_hasher.verify(password, password_hash)


def create_session_token(user: User) -> str:
	now = datetime.now(timezone.utc)
	return jwt.encode(
		{
			"sub": str(user.id),
			"ver": user.token_version,
			"iat": now,
			"exp": now + timedelta(minutes=settings.access_token_minutes),
		},
		settings.jwt_secret_key,
		algorithm=settings.jwt_algorithm,
	)


def new_csrf_token() -> str:
	return secrets.token_urlsafe(32)


def verify_csrf(request: Request) -> None:
	cookie_token = request.cookies.get(settings.csrf_cookie_name, "")
	header_token = request.headers.get("X-CSRF-Token", "")
	if not cookie_token or not header_token or not secrets.compare_digest(cookie_token, header_token):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF validation failed")


def require_csrf(request: Request) -> None:
	verify_csrf(request)


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
	token = request.cookies.get(settings.session_cookie_name)
	if not token:
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
	try:
		payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
		user_id = UUID(payload["sub"])
		token_version = int(payload["ver"])
	except (jwt.InvalidTokenError, KeyError, TypeError, ValueError):
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session") from None

	user = db.get(User, user_id)
	if user is None or not user.is_active or user.token_version != token_version:
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session")
	return user


def permissions_for_user(user: User) -> set[str]:
	return set().union(*(ROLE_PERMISSIONS.get(role.name, set()) for role in user.roles))


def require_permissions(*required: str) -> Callable:
	def permission_dependency(user: User = Depends(get_current_user)) -> User:
		if not set(required).issubset(permissions_for_user(user)):
			raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
		return user

	return permission_dependency