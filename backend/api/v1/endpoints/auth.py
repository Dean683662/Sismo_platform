"""Session endpoints for sign-in, current user, and sign-out."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.api.v1.schemas import LoginRequest, SessionResponse, UserResponse
from backend.core.config import settings
from backend.core.database import get_db
from backend.core.security import (
    create_session_token,
    dummy_password_hash,
    get_current_user,
    hash_password,
    new_csrf_token,
    permissions_for_user,
    require_csrf,
    verify_password,
)
from backend.database.models import AuditLog, Role, User
from backend.services.audit_service import record_audit


router = APIRouter(prefix="/auth", tags=["authentication"])


def to_user_response(user: User) -> UserResponse:
    return UserResponse(
        id=str(user.id),
        full_name=user.full_name,
        email=user.email,
        is_active=user.is_active,
        roles=sorted(role.name for role in user.roles),
        permissions=sorted(permissions_for_user(user)),
    )


def set_session_cookies(response: Response, user: User) -> None:
    response.set_cookie(
        settings.session_cookie_name,
        create_session_token(user),
        max_age=settings.access_token_minutes * 60,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="strict",
        path="/",
    )
    response.set_cookie(
        settings.csrf_cookie_name,
        new_csrf_token(),
        max_age=settings.access_token_minutes * 60,
        httponly=False,
        secure=settings.session_cookie_secure,
        samesite="strict",
        path="/",
    )


@router.post("/login", response_model=SessionResponse)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)) -> SessionResponse:
    normalized_email = str(payload.email).lower()
    user = db.scalar(
        select(User).options(selectinload(User.roles)).where(User.email == normalized_email)
    )
    password_hash = user.password_hash if user else dummy_password_hash
    if not verify_password(payload.password, password_hash) or user is None or not user.is_active:
        db.add(
            AuditLog(
                actor_id=user.id if user else None,
                action="auth.login_failed",
                entity_type="user",
                entity_id=str(user.id) if user else None,
                after_json={"result": "invalid_credentials"},
            )
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    user.last_login_at = datetime.now(timezone.utc)
    record_audit(db, actor_id=user.id, action="auth.login_succeeded", entity_type="user", entity_id=user.id)
    db.commit()
    set_session_cookies(response, user)
    return SessionResponse(user=to_user_response(user))


@router.get("/me", response_model=SessionResponse)
def get_session(user: User = Depends(get_current_user)) -> SessionResponse:
    return SessionResponse(user=to_user_response(user))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_csrf)])
def logout(
    response: Response,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    user.token_version += 1
    record_audit(db, actor_id=user.id, action="auth.logout", entity_type="user", entity_id=user.id)
    db.commit()
    response.delete_cookie(settings.session_cookie_name, path="/", secure=settings.session_cookie_secure, httponly=True, samesite="strict")
    response.delete_cookie(settings.csrf_cookie_name, path="/", secure=settings.session_cookie_secure, samesite="strict")