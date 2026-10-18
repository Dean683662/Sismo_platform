"""FastAPI application entry point."""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from backend.api.v1.router import router as api_v1_router
from backend.core.config import settings
from backend.core.database import engine


app = FastAPI(
	title=settings.app_name,
	version="0.1.0",
	description="Plataforma modular de monitoreo sísmico y analítica.",
)
app.add_middleware(
	CORSMiddleware,
	allow_origins=settings.cors_origin_list,
	allow_credentials=True,
	allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
	allow_headers=["Authorization", "Content-Type", "X-Correlation-ID", "X-CSRF-Token"],
)
app.include_router(api_v1_router, prefix=settings.api_v1_prefix)


@app.middleware("http")
async def security_headers(request: Request, call_next):
	response = await call_next(request)
	response.headers["X-Content-Type-Options"] = "nosniff"
	response.headers["X-Frame-Options"] = "DENY"
	response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
	response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
	if settings.app_environment.lower() in {"production", "prod"}:
		response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
	return response


@app.get("/health", tags=["system"])
def liveness_check() -> dict[str, str]:
	return {"status": "ok", "service": "sismo-platform-api"}


@app.get("/ready", tags=["system"], response_model=None)
def readiness_check() -> dict[str, str] | JSONResponse:
	try:
		with engine.connect() as connection:
			connection.execute(text("SELECT 1"))
	except SQLAlchemyError:
		return JSONResponse(
			status_code=503,
			content={"status": "unavailable", "service": "sismo-platform-api", "dependency": "database"},
		)
	return {"status": "ready", "service": "sismo-platform-api"}