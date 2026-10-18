"""Enable default-deny RLS on application tables for Supabase Data API roles."""

from alembic import op
import sqlalchemy as sa


revision = "20261017_0007"
down_revision = "20261017_0006"
branch_labels = None
depends_on = None


REQUIRED_TABLES = (
	"platform_settings",
	"roles",
	"users",
	"user_roles",
	"audit_logs",
	"data_sources",
	"ingestion_runs",
	"seismic_events",
	"datasets",
	"ml_experiments",
	"alert_rules",
	"alert_deliveries",
	"report_runs",
)

OPTIONAL_TABLES = (
	"model_registry",
	"risk_estimates",
	"report_jobs",
)


def tables_to_protect(existing_tables: set[str]) -> tuple[str, ...]:
	missing_tables = set(REQUIRED_TABLES) - existing_tables
	if missing_tables:
		names = ", ".join(sorted(missing_tables))
		raise RuntimeError(f"Cannot enable Supabase RLS; expected application tables are missing: {names}")
	return REQUIRED_TABLES + tuple(table for table in OPTIONAL_TABLES if table in existing_tables)


def upgrade() -> None:
	if op.get_bind().dialect.name != "postgresql":
		return
	existing_tables = set(sa.inspect(op.get_bind()).get_table_names(schema="public"))
	for table_name in tables_to_protect(existing_tables):
		op.execute(sa.text(f'ALTER TABLE public."{table_name}" ENABLE ROW LEVEL SECURITY'))


def downgrade() -> None:
	if op.get_bind().dialect.name != "postgresql":
		return
	existing_tables = set(sa.inspect(op.get_bind()).get_table_names(schema="public"))
	for table_name in tables_to_protect(existing_tables):
		op.execute(sa.text(f'ALTER TABLE public."{table_name}" DISABLE ROW LEVEL SECURITY'))
