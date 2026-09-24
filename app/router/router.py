from fastapi import APIRouter
from fastapi import Depends
from app.router.v1.router import router as v1_router
from app.router.v2.router import router as v2_router
from app.core.security import require_api_key
router = APIRouter(dependencies=[Depends(require_api_key)])
router.include_router(v1_router)
router.include_router(v2_router)
