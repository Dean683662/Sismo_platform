"""Link the verified IGP source to its official data catalog."""

from alembic import op
import sqlalchemy as sa


revision = "20261018_0008"
down_revision = "20261017_0007"
branch_labels = None
depends_on = None


CATALOG_PAGE = "https://ultimosismo.igp.gob.pe/repositorio/datos-sismicos"
LATEST_EVENT_ENDPOINT = "https://ultimosismo.igp.gob.pe/api/ultimo-sismo"


def upgrade() -> None:
	op.get_bind().execute(
		sa.text(
			"""
			UPDATE data_sources
			SET base_url = :catalog_page
			WHERE provider_key = 'igp' AND base_url = :latest_event_endpoint
			"""
		),
		{"catalog_page": CATALOG_PAGE, "latest_event_endpoint": LATEST_EVENT_ENDPOINT},
	)


def downgrade() -> None:
	op.get_bind().execute(
		sa.text(
			"""
			UPDATE data_sources
			SET base_url = :latest_event_endpoint
			WHERE provider_key = 'igp' AND base_url = :catalog_page
			"""
		),
		{"catalog_page": CATALOG_PAGE, "latest_event_endpoint": LATEST_EVENT_ENDPOINT},
	)
