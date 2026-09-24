from pydantic import BaseModel, Field
from typing import Any

class Metrics(BaseModel):
    original_size: int; compressed_size: int; reduction_percent: float
    ssim: float; psnr: float; processing_time_seconds: float
    iterations: int; params_used: dict[str, Any]

class Job(BaseModel):
    job_id: str; status: str; metrics: Metrics | None = None; download_url: str | None = None; error: str | None = None

class UploadInit(BaseModel):
    filename: str; total_size: int = Field(gt=0); mimetype: str; chunk_size: int = Field(gt=0)

class UploadCreated(BaseModel): upload_id: str; chunk_count: int
