"""Endpoints that validate uploads and enqueue compression jobs."""

import shutil

from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.core.exceptions import ServiceUnavailableError
from app.deps import get_settings
from app.models.v1.response import JobSubmission
from app.services.jobs import create_job
from app.services.storage import save_upload

router = APIRouter(prefix="/compress", tags=["compress"])


@router.post("/image", response_model=JobSubmission, status_code=202)
async def image(
    file: UploadFile = File(...),
    ssim_threshold: float = Form(0.90, ge=0.0, le=1.0),
    settings=Depends(get_settings),
) -> JobSubmission:
    """Persist an image and enqueue the image-specific background pipeline."""
    source = await save_upload(file, settings)
    return JobSubmission(
        job_id=await create_job(source, options={"ssim_threshold": ssim_threshold}),
        status="queued",
    )


@router.post("/video", response_model=JobSubmission, status_code=202)
async def video(
    file: UploadFile = File(...),
    crf: int = Form(28, ge=0, le=51),
    settings=Depends(get_settings),
) -> JobSubmission:
    """Reject early when FFmpeg is unavailable, then enqueue a video job."""
    if not shutil.which(settings.ffmpeg_binary):
        raise ServiceUnavailableError("ffmpeg is unavailable")
    source = await save_upload(file, settings)
    return JobSubmission(
        job_id=await create_job(source, "video", {"crf": crf}),
        status="queued",
    )
