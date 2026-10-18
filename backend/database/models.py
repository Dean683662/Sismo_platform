"""Initial database models shared with Alembic migrations."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, Float, ForeignKey, Integer, JSON, String, Table, Text, Uuid, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base


class PlatformSetting(Base):
    __tablename__ = "platform_settings"

    key: Mapped[str] = mapped_column(String(120), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", String(40), ForeignKey("roles.name", ondelete="CASCADE"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    full_name: Mapped[str] = mapped_column(String(160), nullable=False)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    token_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    roles: Mapped[list["Role"]] = relationship(secondary=user_roles, back_populates="users", lazy="selectin")


class Role(Base):
    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(String(40), primary_key=True)
    description: Mapped[str] = mapped_column(String(200), nullable=False)
    users: Mapped[list[User]] = relationship(secondary=user_roles, back_populates="roles")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(64))
    before_json: Mapped[dict | None] = mapped_column(JSON)
    after_json: Mapped[dict | None] = mapped_column(JSON)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)


class DataSource(Base):
    __tablename__ = "data_sources"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider_key: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    organization: Mapped[str] = mapped_column(String(120), nullable=False)
    base_url: Mapped[str] = mapped_column(String(500), nullable=False)
    source_type: Mapped[str] = mapped_column(String(40), nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active", server_default="active")
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("data_sources.id", ondelete="CASCADE"), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="running", server_default="running")
    records_seen: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    records_inserted: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    records_updated: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    records_duplicated: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    records_skipped: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    error_summary: Mapped[str | None] = mapped_column(String(500))


class SeismicEvent(Base):
    __tablename__ = "seismic_events"
    __table_args__ = (
        UniqueConstraint("source_id", "external_id", name="uq_seismic_event_source_external"),
        CheckConstraint("latitude >= -90 AND latitude <= 90", name="ck_seismic_events_latitude"),
        CheckConstraint("longitude >= -180 AND longitude <= 180", name="ck_seismic_events_longitude"),
        CheckConstraint("magnitude >= 0 AND magnitude <= 10", name="ck_seismic_events_magnitude"),
        CheckConstraint("depth_km >= 0 AND depth_km <= 1000", name="ck_seismic_events_depth"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_id: Mapped[str] = mapped_column(String(100), nullable=False)
    source_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("data_sources.id", ondelete="RESTRICT"), nullable=False, index=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    magnitude: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    magnitude_type: Mapped[str | None] = mapped_column(String(30))
    depth_km: Mapped[float] = mapped_column(Float, nullable=False)
    place: Mapped[str] = mapped_column(String(300), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(500))
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    review_status: Mapped[str] = mapped_column(String(30), nullable=False, default="reported", server_default="reported")


class Dataset(Base):
    __tablename__ = "datasets"
    __table_args__ = (UniqueConstraint("name", "version", name="uq_datasets_name_version"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    query_spec: Mapped[dict] = mapped_column(JSON, nullable=False)
    period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    row_count: Mapped[int] = mapped_column(Integer, nullable=False)
    quality_report: Mapped[dict] = mapped_column(JSON, nullable=False)
    records_json: Mapped[list] = mapped_column(JSON, nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class MLExperiment(Base):
    __tablename__ = "ml_experiments"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    task_type: Mapped[str] = mapped_column(String(30), nullable=False)
    algorithm: Mapped[str] = mapped_column(String(80), nullable=False)
    dataset_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("datasets.id", ondelete="RESTRICT"), nullable=False, index=True)
    feature_spec: Mapped[list] = mapped_column(JSON, nullable=False)
    target_name: Mapped[str] = mapped_column(String(80), nullable=False)
    params: Mapped[dict] = mapped_column(JSON, nullable=False)
    metrics: Mapped[dict] = mapped_column(JSON, nullable=False)
    validation_spec: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="completed", server_default="completed")
    limitations: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class AlertRule(Base):
    __tablename__ = "alert_rules"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    min_magnitude: Mapped[float] = mapped_column(Float, nullable=False)
    min_depth_km: Mapped[float | None] = mapped_column(Float)
    region_bounds: Mapped[dict | None] = mapped_column(JSON)
    source_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    channel: Mapped[str] = mapped_column(String(30), nullable=False, default="in_app", server_default="in_app")
    requires_approval: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    template: Mapped[str] = mapped_column(String(500), nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class AlertDelivery(Base):
    __tablename__ = "alert_deliveries"
    __table_args__ = (UniqueConstraint("deduplication_key", name="uq_alert_deliveries_deduplication_key"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("alert_rules.id", ondelete="CASCADE"), nullable=False, index=True)
    event_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("seismic_events.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(30), nullable=False)
    message: Mapped[str] = mapped_column(String(500), nullable=False)
    deduplication_key: Mapped[str] = mapped_column(String(255), nullable=False)
    is_test: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    last_error: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ReportRun(Base):
    __tablename__ = "report_runs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    filters: Mapped[dict] = mapped_column(JSON, nullable=False)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False)
    records_json: Mapped[list] = mapped_column(JSON, nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)