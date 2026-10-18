"""Tests for the RLS migration's required and optional table handling."""

import importlib.util
from pathlib import Path

import pytest


MIGRATION_PATH = (
	Path(__file__).parents[2]
	/ "backend"
	/ "database"
	/ "migrations"
	/ "versions"
	/ "20261017_0007_supabase_row_level_security.py"
)
SPEC = importlib.util.spec_from_file_location("supabase_rls_migration", MIGRATION_PATH)
assert SPEC is not None and SPEC.loader is not None
migration = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(migration)


def test_rls_migration_protects_existing_application_tables_without_reserved_tables() -> None:
	existing_tables = set(migration.REQUIRED_TABLES)

	assert migration.tables_to_protect(existing_tables) == migration.REQUIRED_TABLES


def test_rls_migration_includes_reserved_tables_if_they_exist() -> None:
	existing_tables = set(migration.REQUIRED_TABLES + migration.OPTIONAL_TABLES)

	assert migration.tables_to_protect(existing_tables) == migration.REQUIRED_TABLES + migration.OPTIONAL_TABLES


def test_rls_migration_reports_missing_required_application_tables() -> None:
	with pytest.raises(RuntimeError, match="expected application tables are missing"):
		migration.tables_to_protect(set(migration.REQUIRED_TABLES) - {"alert_rules"})
