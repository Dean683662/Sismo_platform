"""Environment-backed application settings."""

from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
	app_name: str = "Sismo Platform API"
	app_environment: str = "development"
	api_v1_prefix: str = "/api/v1"
	database_url: str = "postgresql+psycopg://sismo:sismo@localhost:5432/sismo"
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
	igp_latest_event_url: str = "https://ultimosismo.igp.gob.pe/api/ultimo-sismo"

	model_config = SettingsConfigDict(env_file=".env", extra="ignore", env_ignore_empty=True)

	@model_validator(mode="after")
	def validate_production_security(self) -> "Settings":
		if self.app_environment.lower() in {"production", "prod"}:
			if len(self.jwt_secret_key) < 32 or self.jwt_secret_key.startswith("local-development"):
				raise ValueError("JWT_SECRET_KEY must be a unique secret of at least 32 characters in production")
			if not self.session_cookie_secure:
				raise ValueError("SESSION_COOKIE_SECURE must be enabled in production")
		return self

	@property
	def cors_origin_list(self) -> list[str]:
		return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
	return Settings()


settings = get_settings()