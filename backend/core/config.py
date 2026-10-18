"""Environment-backed application settings."""

from functools import lru_cache
from urllib.parse import urlsplit

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL, make_url


class Settings(BaseSettings):
	app_name: str = "Sismo Platform API"
	app_environment: str = "development"
	api_v1_prefix: str = "/api/v1"
	database_url: str = "postgresql+psycopg://sismo:sismo@localhost:5432/sismo"
	supabase_database_url: str | None = None
	db_host: str | None = None
	db_port: int | None = None
	db_database: str | None = None
	db_username: str | None = None
	db_password: SecretStr | None = None
	db_pool_size: int = 5
	db_pool_timeout: int = 30
	db_pool_recycle_seconds: int = 1800
	cors_origins: str = "http://localhost:5173"
	jwt_secret_key: str = "local-development-only-change-before-deployment"
	jwt_algorithm: str = "HS256"
	access_token_minutes: int = 30
	session_cookie_name: str = "sismo_session"
	csrf_cookie_name: str = "sismo_csrf"
	session_cookie_secure: bool = False
	bootstrap_admin_email: str | None = None
	bootstrap_admin_name: str = "Administrador"
	bootstrap_admin_password: str | None = None
	alert_webhook_url: SecretStr | None = None
	alert_webhook_timeout_seconds: int = 5
	igp_latest_event_url: str = "https://ultimosismo.igp.gob.pe/api/ultimo-sismo"

	model_config = SettingsConfigDict(env_file=".env", extra="ignore", env_ignore_empty=True)

	@model_validator(mode="after")
	def validate_production_security(self) -> "Settings":
		if self.db_pool_size < 1 or self.db_pool_timeout < 1 or self.db_pool_recycle_seconds < 1:
			raise ValueError("Database pool settings must be positive")
		provided_db_fields = (
			self.db_host,
			self.db_port,
			self.db_database,
			self.db_username,
			self.db_password,
		)
		if any(value is not None for value in provided_db_fields) and not all(
			value is not None for value in provided_db_fields
		):
			raise ValueError("Set all five database fields: DB_HOST, DB_PORT, DB_DATABASE, DB_USERNAME, DB_PASSWORD")
		if self.db_host is not None and (
			not self.db_host.endswith(".pooler.supabase.com") or self.db_port != 5432
		):
			raise ValueError("DB_HOST and DB_PORT must identify the Supabase Session Pooler on port 5432")
		if self.alert_webhook_timeout_seconds < 1 or self.alert_webhook_timeout_seconds > 30:
			raise ValueError("ALERT_WEBHOOK_TIMEOUT_SECONDS must be between 1 and 30")
		if self.alert_webhook_url is not None:
			parsed_webhook = urlsplit(self.alert_webhook_url.get_secret_value())
			local_webhook_hosts = {"localhost", "127.0.0.1", "::1"}
			allow_http = self.app_environment.lower() not in {"production", "prod"}
			if (
				parsed_webhook.scheme not in ({"https", "http"} if allow_http else {"https"})
				or not parsed_webhook.hostname
				or parsed_webhook.username is not None
				or parsed_webhook.password is not None
				or parsed_webhook.fragment
				or (parsed_webhook.scheme == "http" and parsed_webhook.hostname not in local_webhook_hosts)
			):
				raise ValueError("ALERT_WEBHOOK_URL must be HTTPS (HTTP is allowed only for local development)")
		if self.supabase_database_url:
			try:
				url = make_url(self.supabase_database_url)
			except (TypeError, ValueError) as error:
				raise ValueError("SUPABASE_DATABASE_URL must be a valid PostgreSQL URL") from error
			if (
				url.drivername not in {"postgres", "postgresql", "postgresql+psycopg"}
				or not url.host
				or not url.host.endswith(".pooler.supabase.com")
				or url.port != 5432
			):
				raise ValueError(
					"SUPABASE_DATABASE_URL must use the Supabase Session Pooler host on port 5432"
				)
		if self.app_environment.lower() in {"production", "prod"}:
			if len(self.jwt_secret_key) < 32 or self.jwt_secret_key.startswith("local-development"):
				raise ValueError("JWT_SECRET_KEY must be a unique secret of at least 32 characters in production")
			if not self.session_cookie_secure:
				raise ValueError("SESSION_COOKIE_SECURE must be enabled in production")
		return self

	@property
	def cors_origin_list(self) -> list[str]:
		return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

	@property
	def effective_database_url(self) -> str:
		if self.db_host is not None:
			url = URL.create(
				drivername="postgresql+psycopg",
				username=self.db_username,
				password=self.db_password.get_secret_value() if self.db_password else None,
				host=self.db_host,
				port=self.db_port,
				database=self.db_database,
			)
			return url.render_as_string(hide_password=False)
		return self.supabase_database_url or self.database_url

	@property
	def uses_supabase_session_pooler(self) -> bool:
		if self.db_host is not None:
			return True
		if not self.supabase_database_url:
			return False
		return make_url(self.supabase_database_url).host.endswith(".pooler.supabase.com")


@lru_cache
def get_settings() -> Settings:
	return Settings()


settings = get_settings()