"""Track source rows omitted because required event data is missing."""

from alembic import op
import sqlalchemy as sa


revision = "20261018_0009"
down_revision = "20261018_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
	op.add_column(
		"ingestion_runs",
		sa.Column("records_skipped", sa.Integer(), server_default="0", nullable=False),
	)


def downgrade() -> None:
	op.drop_column("ingestion_runs", "records_skipped")
