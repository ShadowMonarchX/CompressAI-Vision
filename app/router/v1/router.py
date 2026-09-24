from fastapi import APIRouter
from .endpoints import health, compress, jobs, upload, compare
router = APIRouter(prefix='/api/v1')
for module in (health, compress, jobs, upload, compare): router.include_router(module.router)
