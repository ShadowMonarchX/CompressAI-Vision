"""Read-only service health and client configuration endpoints."""

import shutil

from fastapi import APIRouter, Depends

from app.deps import get_settings
from app.models.v1.response import AppConfig, Health

router = APIRouter(tags=["health"])


@router.get('/health',response_model=Health)
async def health(settings=Depends(get_settings)) -> Health:
    """Report dependencies needed by the browser and compression workers."""
    return Health(status="ok", ffmpeg=bool(shutil.which(settings.ffmpeg_binary)), workers=settings.max_workers or 1, chunk_size=settings.chunk_size)


@router.get('/config',response_model=AppConfig)
async def config(settings=Depends(get_settings)) -> AppConfig:
    """Expose safe limits without returning secrets or internal paths."""
    return AppConfig(max_file_size=settings.max_file_size, small_file_threshold=settings.small_file_threshold, chunk_size=settings.chunk_size, ssim_threshold=settings.ssim_threshold)
