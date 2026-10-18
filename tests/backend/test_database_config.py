"""Supabase Session Pooler URL and connection-pool configuration checks."""

import pytest
from pydantic import ValidationError

from backend.core import database
from backend.core.config import Settings


def test_supabase_session_pooler_url_uses_psycopg_tls(monkeypatch: pytest.MonkeyPatch) -> None:
	settings = Settings(
		_env_file=None,
		database_url="postgresql+psycopg://local:local@localhost:5432/sismo",
		supabase_database_url=(
			"postgresql://postgres.project-ref:encoded%40password@"
			"aws-0-us-east-1.pooler.supabase.com:5432/postgres"
		),
	)
	monkeypatch.setattr(database, "settings", settings)

	url = database.get_database_url()

	assert url.drivername == "postgresql+psycopg"
	assert url.host == "aws-0-us-east-1.pooler.supabase.com"
	assert url.port == 5432
	assert url.database == "postgres"
	assert url.password == "encoded@password"
	assert url.query["sslmode"] == "require"


def test_supabase_session_pooler_fields_build_encoded_url_and_require_tls(
	monkeypatch: pytest.MonkeyPatch,
) -> None:
	settings = Settings(
		_env_file=None,
		db_host="aws-0-us-east-1.pooler.supabase.com",
		db_port=5432,
		db_database="postgres",
		db_username="postgres.project-ref",
		db_password="secret@with:/chars",
	)
	monkeypatch.setattr(database, "settings", settings)

	url = database.get_database_url()

	assert url.drivername == "postgresql+psycopg"
	assert url.username == "postgres.project-ref"
	assert url.password == "secret@with:/chars"
	assert url.database == "postgres"
	assert url.port == 5432
	assert url.query["sslmode"] == "require"


@pytest.mark.parametrize(
	"values",
	[
		{"db_host": "aws-0-us-east-1.pooler.supabase.com"},
		{
			"db_host": "db.example.com",
			"db_port": 5432,
			"db_database": "postgres",
			"db_username": "postgres",
			"db_password": "secret",
		},
		{
			"db_host": "aws-0-us-east-1.pooler.supabase.com",
			"db_port": 6543,
			"db_database": "postgres",
			"db_username": "postgres",
			"db_password": "secret",
		},
	],
)
def test_supabase_connection_fields_require_complete_session_pooler(values: dict[str, object]) -> None:
	with pytest.raises(ValidationError):
		Settings(_env_file=None, **values)


@pytest.mark.parametrize(
	"url",
	[
		"postgresql://postgres:password@db.example.com:5432/postgres",
		"postgresql://postgres.project-ref@aws-0-us-east-1.pooler.supabase.com:6543/postgres",
	],
)
def test_supabase_configuration_rejects_non_session_pooler(url: str) -> None:
	with pytest.raises(ValidationError, match="Session Pooler"):
		Settings(_env_file=None, supabase_database_url=url)


def test_pool_settings_must_be_positive() -> None:
	with pytest.raises(ValidationError, match="pool settings must be positive"):
		Settings(_env_file=None, db_pool_size=0)
