import shutil
from fastapi import APIRouter, Depends
from app.deps import get_settings
from app.models.v1.response import Health, AppConfig
router=APIRouter(tags=['health'])
@router.get('/health',response_model=Health)
async def health(settings=Depends(get_settings)): return {'status':'ok','ffmpeg':bool(shutil.which(settings.ffmpeg_binary)),'workers':settings.max_workers or 1,'chunk_size':settings.chunk_size}
@router.get('/config',response_model=AppConfig)
async def config(settings=Depends(get_settings)): return {k:getattr(settings,k) for k in ('max_file_size','small_file_threshold','chunk_size','ssim_threshold')}
