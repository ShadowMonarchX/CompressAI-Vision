import shutil
from fastapi import APIRouter, Depends, File, UploadFile
from app.api.deps import get_job_store, get_settings
from app.core.exceptions import ServiceUnavailableError
from app.schemas.models import JobSubmission
from app.services.jobs import create_job
from app.services.storage import save_upload
router=APIRouter(prefix="/compress",tags=["compression"])
@router.post("/image",response_model=JobSubmission,status_code=202)
async def image(file:UploadFile=File(...),settings=Depends(get_settings),store=Depends(get_job_store)): return {"job_id":await create_job(await save_upload(file,settings)),"status":"queued"}
@router.post("/video",response_model=JobSubmission,status_code=202)
async def video(file:UploadFile=File(...),settings=Depends(get_settings),store=Depends(get_job_store)):
    if not shutil.which(settings.ffmpeg_binary): raise ServiceUnavailableError("ffmpeg is unavailable")
    return {"job_id":await create_job(await save_upload(file,settings)),"status":"queued"}
