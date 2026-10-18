"""Prepare a disposable SQLite database for the Playwright browser suite."""

import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.config import Config
from sqlalchemy import select


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///./sismo-e2e.sqlite")

config = Config(str(REPOSITORY_ROOT / "alembic.ini"))
config.set_main_option("script_location", str(REPOSITORY_ROOT / "backend" / "database" / "migrations"))
command.upgrade(config, "head")

from backend.core.database import SessionLocal
from backend.core.security import hash_password
from backend.database.models import DataSource, Role, SeismicEvent, User


email = os.environ.get("BOOTSTRAP_ADMIN_EMAIL", "e2e-admin@example.com")
password = os.environ.get("BOOTSTRAP_ADMIN_PASSWORD", "E2E-Only-Password-2026")

with SessionLocal.begin() as db:
	role = db.get(Role, "administrator")
	if role is None:
		raise RuntimeError("The administrator role was not created by migrations")
	db.add(
		User(
			full_name="E2E Administrator",
			email=email,
			password_hash=hash_password(password),
			roles=[role],
		)
	)
	source = DataSource(
		provider_key="e2e",
		name="E2E verified source",
		organization="Isolated test fixture",
		base_url="https://example.test/e2e",
		source_type="official_api",
		status="active",
		is_verified=True,
	)
	db.add(source)
	db.flush()
	db.add(
		SeismicEvent(
			external_id=f"e2e-{uuid4()}",
			source_id=source.id,
			occurred_at=datetime.now(timezone.utc),
			latitude=-12.0464,
			longitude=-77.0428,
			magnitude=4.2,
			depth_km=20,
			place="E2E fixture, Lima",
			source_url=source.base_url,
			payload_hash=hashlib.sha256(uuid4().bytes).hexdigest(),
		)
	)

print("Isolated E2E database migrated and seeded")
