"""Persist immutable datasets and reproducible ML experiment metadata."""

from alembic import op
import sqlalchemy as sa


revision = "20261016_0004"
down_revision = "20261015_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
	op.create_table(
		"datasets",
		sa.Column("id", sa.Uuid(), nullable=False),
		sa.Column("name", sa.String(length=160), nullable=False),
		sa.Column("version", sa.Integer(), nullable=False),
		sa.Column("query_spec", sa.JSON(), nullable=False),
		sa.Column("period_start", sa.DateTime(timezone=True), nullable=True),
		sa.Column("period_end", sa.DateTime(timezone=True), nullable=True),
		sa.Column("row_count", sa.Integer(), nullable=False),
		sa.Column("quality_report", sa.JSON(), nullable=False),
		sa.Column("records_json", sa.JSON(), nullable=False),
		sa.Column("created_by", sa.Uuid(), nullable=True),
		sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
	sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
		sa.PrimaryKeyConstraint("id"),
		sa.UniqueConstraint("name", "version", name="uq_datasets_name_version"),
	)
	op.create_index("ix_datasets_name", "datasets", ["name"])
	op.create_table(
		"ml_experiments",
		sa.Column("id", sa.Uuid(), nullable=False),
		sa.Column("name", sa.String(length=160), nullable=False),
		sa.Column("task_type", sa.String(length=30), nullable=False),
		sa.Column("algorithm", sa.String(length=80), nullable=False),
		sa.Column("dataset_id", sa.Uuid(), nullable=False),
		sa.Column("feature_spec", sa.JSON(), nullable=False),
		sa.Column("target_name", sa.String(length=80), nullable=False),
		sa.Column("params", sa.JSON(), nullable=False),
		sa.Column("metrics", sa.JSON(), nullable=False),
		sa.Column("validation_spec", sa.JSON(), nullable=False),
		sa.Column("status", sa.String(length=30), server_default="completed", nullable=False),
		sa.Column("limitations", sa.Text(), nullable=False),
		sa.Column("created_by", sa.Uuid(), nullable=True),
		sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
		sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
		sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"], ondelete="RESTRICT"),
		sa.PrimaryKeyConstraint("id"),
	)
	op.create_index("ix_ml_experiments_dataset_id", "ml_experiments", ["dataset_id"])


def downgrade() -> None:
	op.drop_index("ix_ml_experiments_dataset_id", table_name="ml_experiments")
	op.drop_table("ml_experiments")
	op.drop_index("ix_datasets_name", table_name="datasets")
	op.drop_table("datasets")