"""Validated request bodies for identity and administration endpoints."""

from typing import Literal

from datetime import datetime, timezone

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
    records_skipped: int
    error_summary: str | None


class DataSourceResponse(BaseModel):
    id: str
    provider_key: str
    name: str
    organization: str
    base_url: str
    source_type: str
    is_verified: bool
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
    task_type: Literal["regression", "classification"] = "regression"


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


class AlertRuleCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    is_enabled: bool = True
    min_magnitude: float = Field(ge=0, le=10)
    min_depth_km: float | None = Field(default=None, ge=0, le=1000)
    region_bounds: dict[str, float] | None = None
    source_ids: list[str] = Field(default_factory=list, max_length=20)
    channel: Literal["in_app", "webhook"] = "in_app"
    requires_approval: bool = False
    template: str = Field(
        default="Sismo de magnitud {magnitude} en {place} (fuente: {source_name}).",
        min_length=1,
        max_length=500,
    )

    @model_validator(mode="after")
    def validate_region_and_template(self) -> "AlertRuleCreateRequest":
        _validate_region_bounds(self.region_bounds)
        _validate_alert_template(self.template)
        return self


class AlertRuleUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    is_enabled: bool | None = None
    min_magnitude: float | None = Field(default=None, ge=0, le=10)
    min_depth_km: float | None = Field(default=None, ge=0, le=1000)
    region_bounds: dict[str, float] | None = None
    source_ids: list[str] | None = Field(default=None, max_length=20)
    channel: Literal["in_app", "webhook"] | None = None
    requires_approval: bool | None = None
    template: str | None = Field(default=None, min_length=1, max_length=500)

    @model_validator(mode="after")
    def validate_changes(self) -> "AlertRuleUpdateRequest":
        if not self.model_fields_set:
            raise ValueError("At least one field must be updated")
        required_values = {"name", "is_enabled", "min_magnitude", "source_ids", "channel", "requires_approval", "template"}
        if any(getattr(self, field) is None for field in self.model_fields_set & required_values):
            raise ValueError("Updated rule fields cannot be null")
        if "region_bounds" in self.model_fields_set:
            _validate_region_bounds(self.region_bounds)
        if self.template is not None:
            _validate_alert_template(self.template)
        return self


def _validate_region_bounds(bounds: dict[str, float] | None) -> None:
    if bounds is None:
        return
    if set(bounds) != {"min_latitude", "max_latitude", "min_longitude", "max_longitude"}:
        raise ValueError("region_bounds must define min/max latitude and longitude")
    if not (-90 <= bounds["min_latitude"] < bounds["max_latitude"] <= 90):
        raise ValueError("region latitude bounds are invalid")
    if not (-180 <= bounds["min_longitude"] < bounds["max_longitude"] <= 180):
        raise ValueError("region longitude bounds are invalid")


def _validate_alert_template(template: str) -> None:
    from string import Formatter

    allowed_fields = {"magnitude", "place", "occurred_at", "source_name"}
    try:
        parts = list(Formatter().parse(template))
    except ValueError as error:
        raise ValueError("template contains invalid formatting syntax") from error
    fields = {field for _, field, _, _ in parts if field is not None}
    if not fields.issubset(allowed_fields) or any(
        field is not None and (conversion is not None or format_spec)
        for _, field, format_spec, conversion in parts
    ):
        raise ValueError("template fields must be magnitude, place, occurred_at, or source_name")


class AlertRuleResponse(BaseModel):
    id: str
    name: str
    is_enabled: bool
    min_magnitude: float
    min_depth_km: float | None
    region_bounds: dict[str, float] | None
    source_ids: list[str]
    channel: str
    requires_approval: bool
    template: str
    created_at: datetime
    updated_at: datetime


class AlertDeliveryResponse(BaseModel):
    id: str
    rule_id: str
    rule_name: str
    event_id: str
    source_name: str
    source_url: str | None
    event_magnitude: float
    event_place: str
    event_occurred_at: datetime
    status: Literal["pending_approval", "queued", "delivered", "rejected", "failed"]
    channel: str
    message: str
    is_test: bool
    attempt_count: int
    last_error: str | None
    created_at: datetime
    delivered_at: datetime | None
    reviewed_at: datetime | None


class AlertTestRequest(BaseModel):
    source_id: str | None = None


class PlatformSettingsResponse(BaseModel):
    audit_retention_days: int
    alert_history_retention_days: int
    report_retention_days: int


class PlatformSettingsUpdateRequest(BaseModel):
    audit_retention_days: int = Field(ge=30, le=3650)
    alert_history_retention_days: int = Field(ge=7, le=3650)
    report_retention_days: int = Field(ge=30, le=3650)


class ReportCreateRequest(BaseModel):
    report_type: Literal["events", "models", "sources", "alerts", "quality"]
    start_date: datetime | None = None
    end_date: datetime | None = None
    min_magnitude: float | None = Field(default=None, ge=0, le=10)
    max_magnitude: float | None = Field(default=None, ge=0, le=10)
    source_key: str | None = Field(default=None, max_length=40)
    limit: int = Field(default=5000, ge=1, le=50000)

    @model_validator(mode="after")
    def validate_report_filters(self) -> "ReportCreateRequest":
        start_date = self.start_date.replace(tzinfo=self.start_date.tzinfo or timezone.utc).astimezone(timezone.utc) if self.start_date else None
        end_date = self.end_date.replace(tzinfo=self.end_date.tzinfo or timezone.utc).astimezone(timezone.utc) if self.end_date else None
        if start_date and end_date and start_date > end_date:
            raise ValueError("start_date must not be after end_date")
        if self.min_magnitude is not None and self.max_magnitude is not None and self.min_magnitude > self.max_magnitude:
            raise ValueError("min_magnitude must not exceed max_magnitude")
        if self.report_type != "events" and (
            self.min_magnitude is not None or self.max_magnitude is not None or self.source_key is not None
        ):
            raise ValueError("magnitude and source filters are only valid for event reports")
        return self


class ReportResponse(BaseModel):
    id: str
    report_type: Literal["events", "models", "sources", "alerts", "quality"]
    filters: dict
    row_count: int
    requested_by: str | None
    created_at: datetime