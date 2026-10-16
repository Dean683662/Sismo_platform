"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.v1.router import router as api_v1_router
from backend.core.config import settings


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


@app.get("/health", tags=["system"])
def liveness_check() -> dict[str, str]:
	return {"status": "ok", "service": "sismo-platform-api"}