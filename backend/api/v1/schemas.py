"""Validated request bodies for identity and administration endpoints."""

from typing import Literal

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


RoleName = Literal["administrator", "analyst", "alert_operator", "auditor", "read_only"]


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class CreateUserRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=160)
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    roles: list[RoleName] = Field(min_length=1, max_length=5)


class UpdateUserRequest(BaseModel):
    is_active: bool | None = None
    roles: list[RoleName] | None = Field(default=None, min_length=1, max_length=5)

    @model_validator(mode="after")
    def require_at_least_one_change(self) -> "UpdateUserRequest":
        if self.is_active is None and self.roles is None:
            raise ValueError("At least one field must be updated")
        return self


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    full_name: str
    email: str
    is_active: bool
    roles: list[str]
    permissions: list[str]


class SessionResponse(BaseModel):
    user: UserResponse


class AuditLogResponse(BaseModel):
    id: str
    actor_id: str | None
    action: str
    entity_type: str
    entity_id: str | None
    before_json: dict | None
    after_json: dict | None
    occurred_at: str


class RoleResponse(BaseModel):
    name: RoleName
    description: str
    permissions: list[str]


class EventResponse(BaseModel):
    id: str
    external_id: str
    source_key: str
    occurred_at: datetime
    latitude: float
    longitude: float
    magnitude: float
    magnitude_type: str | None
    depth_km: float
    place: str
    source_url: str | None
    received_at: datetime
    review_status: str


class EventPageResponse(BaseModel):
    items: list[EventResponse]
    total: int
    limit: int
    offset: int


class IngestionRunSummary(BaseModel):
    id: str
    started_at: datetime
    finished_at: datetime | None
    status: str
    records_seen: int
    records_inserted: int
    records_updated: int
    records_duplicated: int
    error_summary: str | None


class DataSourceResponse(BaseModel):
    id: str
    provider_key: str
    name: str
    organization: str
    base_url: str
    source_type: str
    status: str
    last_sync_at: datetime | None
    last_success_at: datetime | None
    last_run: IngestionRunSummary | None


class SyncRunResponse(IngestionRunSummary):
    source_id: str