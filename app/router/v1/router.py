"""Version 1 route aggregator."""

from fastapi import APIRouter

from .endpoints import health, compress, jobs, upload, compare

router = APIRouter(prefix="/api/v1")

# Keeping registration in one place makes the public v1 surface auditable and
# ensures every endpoint receives the same API-version prefix.
for module in (health, compress, jobs, upload, compare):
    router.include_router(module.router)
