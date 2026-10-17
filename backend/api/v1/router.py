"""Version 1 API router."""

from fastapi import APIRouter

from backend.api.v1.endpoints import admin, analytics, auth, datasets, events, ml, sources

router = APIRouter()
router.include_router(auth.router)
router.include_router(admin.router)
router.include_router(analytics.router)
router.include_router(events.router)
router.include_router(sources.router)
router.include_router(datasets.router)
router.include_router(ml.router)


@router.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
	return {"status": "ok", "service": "sismo-platform-api"}