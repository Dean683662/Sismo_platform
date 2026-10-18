"""Add verified sources, alert rules and delivery history."""

from alembic import op
import sqlalchemy as sa


revision = "20261017_0005"
down_revision = "20261016_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "data_sources",
        sa.Column("is_verified", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.execute(
        sa.text("UPDATE data_sources SET is_verified = true WHERE provider_key = 'igp' AND source_type = 'official_api'")
    )
    op.create_table(
        "alert_rules",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("min_magnitude", sa.Float(), nullable=False),
        sa.Column("min_depth_km", sa.Float(), nullable=True),
        sa.Column("region_bounds", sa.JSON(), nullable=True),
        sa.Column("source_ids", sa.JSON(), nullable=False),
        sa.Column("channel", sa.String(length=30), server_default="in_app", nullable=False),
        sa.Column("requires_approval", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("template", sa.String(length=500), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "alert_deliveries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("rule_id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("channel", sa.String(length=30), nullable=False),
        sa.Column("message", sa.String(length=500), nullable=False),
        sa.Column("deduplication_key", sa.String(length=255), nullable=False),
        sa.Column("is_test", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_error", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by", sa.Uuid(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["event_id"], ["seismic_events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["rule_id"], ["alert_rules.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("deduplication_key", name="uq_alert_deliveries_deduplication_key"),
    )
    op.create_index("ix_alert_deliveries_rule_id", "alert_deliveries", ["rule_id"])
    op.create_index("ix_alert_deliveries_event_id", "alert_deliveries", ["event_id"])
    op.create_index("ix_alert_deliveries_status", "alert_deliveries", ["status"])
    op.create_index("ix_alert_deliveries_created_at", "alert_deliveries", ["created_at"])
    op.create_table(
        "report_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("report_type", sa.String(length=30), nullable=False),
        sa.Column("filters", sa.JSON(), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("records_json", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_report_runs_report_type", "report_runs", ["report_type"])
    op.create_index("ix_report_runs_created_at", "report_runs", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_report_runs_created_at", table_name="report_runs")
    op.drop_index("ix_report_runs_report_type", table_name="report_runs")
    op.drop_table("report_runs")
    op.drop_index("ix_alert_deliveries_created_at", table_name="alert_deliveries")
    op.drop_index("ix_alert_deliveries_status", table_name="alert_deliveries")
    op.drop_index("ix_alert_deliveries_event_id", table_name="alert_deliveries")
    op.drop_index("ix_alert_deliveries_rule_id", table_name="alert_deliveries")
    op.drop_table("alert_deliveries")
    op.drop_table("alert_rules")
    op.drop_column("data_sources", "is_verified")
