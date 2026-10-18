"""SQLAlchemy engine, base model, and request-scoped sessions."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from backend.core.config import settings


def get_database_url() -> URL:
	database_url = make_url(settings.effective_database_url)
	if database_url.drivername in {"postgres", "postgresql"}:
		database_url = database_url.set(drivername="postgresql+psycopg")
	if settings.uses_supabase_session_pooler:
		query = dict(database_url.query)
		query["sslmode"] = "require"
		database_url = database_url.set(query=query)
	return database_url


database_url = get_database_url()
engine_options = {"pool_pre_ping": True}
if not database_url.drivername.startswith("sqlite"):
	engine_options.update(
		pool_size=settings.db_pool_size,
		max_overflow=0,
		pool_timeout=settings.db_pool_timeout,
		pool_recycle=settings.db_pool_recycle_seconds,
	)
engine = create_engine(database_url, **engine_options)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
	pass


def get_db() -> Generator[Session, None, None]:
	session = SessionLocal()
	try:
		yield session
	finally:
		session.close()