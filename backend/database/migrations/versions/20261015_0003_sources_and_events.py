"""Add data sources, ingestion runs, and normalized seismic events."""

import uuid

from alembic import op
import sqlalchemy as sa


revision = "20261015_0003"
down_revision = "20261015_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
	op.create_table(
		"data_sources",
		sa.Column("id", sa.Uuid(), nullable=False),
		sa.Column("provider_key", sa.String(length=40), nullable=False),
		sa.Column("name", sa.String(length=120), nullable=False),
		sa.Column("organization", sa.String(length=120), nullable=False),
		sa.Column("base_url", sa.String(length=500), nullable=False),
		sa.Column("source_type", sa.String(length=40), nullable=False),
		sa.Column("status", sa.String(length=20), server_default="active", nullable=False),
		sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
		sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
		sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
		sa.PrimaryKeyConstraint("id"),
		sa.UniqueConstraint("provider_key"),
	)
	op.create_table(
		"ingestion_runs",
		sa.Column("id", sa.Uuid(), nullable=False),
		sa.Column("source_id", sa.Uuid(), nullable=False),
		sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
		sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
		sa.Column("status", sa.String(length=20), server_default="running", nullable=False),
		sa.Column("records_seen", sa.Integer(), server_default="0", nullable=False),
		sa.Column("records_inserted", sa.Integer(), server_default="0", nullable=False),
		sa.Column("records_updated", sa.Integer(), server_default="0", nullable=False),
		sa.Column("records_duplicated", sa.Integer(), server_default="0", nullable=False),
		sa.Column("error_summary", sa.String(length=500), nullable=True),
		sa.ForeignKeyConstraint(["source_id"], ["data_sources.id"], ondelete="CASCADE"),
		sa.PrimaryKeyConstraint("id"),
	)
	op.create_index("ix_ingestion_runs_source_id", "ingestion_runs", ["source_id"])
	op.create_table(
		"seismic_events",
		sa.Column("id", sa.Uuid(), nullable=False),
		sa.Column("external_id", sa.String(length=100), nullable=False),
		sa.Column("source_id", sa.Uuid(), nullable=False),
		sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
		sa.Column("latitude", sa.Float(), nullable=False),
		sa.Column("longitude", sa.Float(), nullable=False),
		sa.Column("magnitude", sa.Float(), nullable=False),
		sa.Column("magnitude_type", sa.String(length=30), nullable=True),
		sa.Column("depth_km", sa.Float(), nullable=False),
		sa.Column("place", sa.String(length=300), nullable=False),
		sa.Column("source_url", sa.String(length=500), nullable=True),
		sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
		sa.Column("payload_hash", sa.String(length=64), nullable=False),
		sa.Column("review_status", sa.String(length=30), server_default="reported", nullable=False),
		sa.CheckConstraint("latitude >= -90 AND latitude <= 90", name="ck_seismic_events_latitude"),
		sa.CheckConstraint("longitude >= -180 AND longitude <= 180", name="ck_seismic_events_longitude"),
		sa.CheckConstraint("magnitude >= 0 AND magnitude <= 10", name="ck_seismic_events_magnitude"),
		sa.CheckConstraint("depth_km >= 0 AND depth_km <= 1000", name="ck_seismic_events_depth"),
		sa.ForeignKeyConstraint(["source_id"], ["data_sources.id"], ondelete="RESTRICT"),
		sa.PrimaryKeyConstraint("id"),
		sa.UniqueConstraint("source_id", "external_id", name="uq_seismic_event_source_external"),
	)
	op.create_index("ix_seismic_events_source_id", "seismic_events", ["source_id"])
	op.create_index("ix_seismic_events_occurred_at", "seismic_events", ["occurred_at"])
	op.create_index("ix_seismic_events_magnitude", "seismic_events", ["magnitude"])

	data_sources = sa.table(
		"data_sources",
		sa.column("id", sa.Uuid()),
		sa.column("provider_key", sa.String()),
		sa.column("name", sa.String()),
		sa.column("organization", sa.String()),
		sa.column("base_url", sa.String()),
		sa.column("source_type", sa.String()),
		sa.column("status", sa.String()),
	)
	op.bulk_insert(
		data_sources,
		[
			{
				"id": uuid.uuid4(),
				"provider_key": "igp",
				"name": "Último sismo reportado",
				"organization": "Instituto Geofísico del Perú",
				"base_url": "https://ultimosismo.igp.gob.pe/repositorio/datos-sismicos",
				"source_type": "official_api",
				"status": "active",
			}
		],
	)


def downgrade() -> None:
	op.drop_index("ix_seismic_events_magnitude", table_name="seismic_events")
	op.drop_index("ix_seismic_events_occurred_at", table_name="seismic_events")
	op.drop_index("ix_seismic_events_source_id", table_name="seismic_events")
	op.drop_table("seismic_events")
	op.drop_index("ix_ingestion_runs_source_id", table_name="ingestion_runs")
	op.drop_table("ingestion_runs")
	op.drop_table("data_sources")