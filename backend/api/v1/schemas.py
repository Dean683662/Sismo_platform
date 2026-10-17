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


class DashboardSummaryResponse(BaseModel):
    total_events: int
    events_last_24h: int
    latest_event_at: datetime | None
    active_sources: int
    total_sources: int
    last_sync_at: datetime | None


class TimeSeriesPoint(BaseModel):
    period_start: datetime
    event_count: int


class TimeSeriesResponse(BaseModel):
    items: list[TimeSeriesPoint]
    total_events: int
    period_start: datetime
    period_end: datetime
    group_by: Literal["day", "week"]


class DatasetCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    start_date: datetime | None = None
    end_date: datetime | None = None
    min_magnitude: float | None = Field(default=None, ge=0, le=10)
    max_magnitude: float | None = Field(default=None, ge=0, le=10)

    @model_validator(mode="after")
    def validate_ranges(self) -> "DatasetCreateRequest":
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("start_date must not be after end_date")
        if self.min_magnitude is not None and self.max_magnitude is not None and self.min_magnitude > self.max_magnitude:
            raise ValueError("min_magnitude must not exceed max_magnitude")
        return self


class DatasetResponse(BaseModel):
    id: str
    name: str
    version: int
    query_spec: dict
    period_start: datetime | None
    period_end: datetime | None
    row_count: int
    quality_report: dict
    created_at: datetime


class ExperimentCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    dataset_id: str
    test_fraction: float = Field(default=0.2, ge=0.1, le=0.5)


class ExperimentResponse(BaseModel):
    id: str
    name: str
    task_type: str
    algorithm: str
    dataset_id: str
    feature_spec: list[str]
    target_name: str
    params: dict
    metrics: dict[str, float]
    validation_spec: dict
    status: str
    limitations: str
    created_at: datetime