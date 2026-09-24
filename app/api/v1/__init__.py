from fastapi import APIRouter
from .routers.compress import router as compress_router
from .routers.jobs import router as jobs_router
from .routers.health import router as health_router
from .routers.upload import router as upload_router
router=APIRouter(prefix="/api/v1")
for child in (compress_router,upload_router,jobs_router,health_router): router.include_router(child)
