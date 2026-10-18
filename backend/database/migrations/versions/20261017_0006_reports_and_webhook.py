"""Support quality reports and webhook deliveries."""

from alembic import op
import sqlalchemy as sa


revision = "20261017_0006"
down_revision = "20261017_0005"
branch_labels = None
depends_on = None


def _replace_check(table_name: str, constraint_name: str, expression: str) -> None:
	bind = op.get_bind()
	existing = {
		constraint.get("name")
		for constraint in sa.inspect(bind).get_check_constraints(table_name)
	}
	with op.batch_alter_table(table_name) as batch:
		if constraint_name in existing:
			batch.drop_constraint(constraint_name, type_="check")
		batch.create_check_constraint(constraint_name, expression)


def upgrade() -> None:
	_replace_check("alert_rules", "ck_alert_rules_channel", "channel IN ('in_app', 'webhook')")
	_replace_check("alert_deliveries", "ck_alert_deliveries_channel", "channel IN ('in_app', 'webhook')")
	_replace_check(
		"alert_deliveries",
		"ck_alert_deliveries_status",
		"status IN ('queued', 'pending_approval', 'delivered', 'rejected', 'failed')",
	)
	_replace_check(
		"report_runs",
		"ck_report_runs_type",
		"report_type IN ('events', 'models', 'sources', 'alerts', 'quality')",
	)


def downgrade() -> None:
	op.execute(sa.text("UPDATE alert_rules SET channel = 'in_app' WHERE channel = 'webhook'"))
	op.execute(sa.text("UPDATE alert_deliveries SET channel = 'in_app' WHERE channel = 'webhook'"))
	op.execute(sa.text("UPDATE alert_deliveries SET status = 'failed' WHERE status = 'queued'"))
	op.execute(sa.text("UPDATE report_runs SET report_type = 'events' WHERE report_type = 'quality'"))
	_replace_check("alert_rules", "ck_alert_rules_channel", "channel = 'in_app'")
	_replace_check("alert_deliveries", "ck_alert_deliveries_channel", "channel = 'in_app'")
	_replace_check(
		"alert_deliveries",
		"ck_alert_deliveries_status",
		"status IN ('pending_approval', 'delivered', 'rejected', 'failed')",
	)
	_replace_check(
		"report_runs",
		"ck_report_runs_type",
		"report_type IN ('events', 'models', 'sources', 'alerts')",
	)
