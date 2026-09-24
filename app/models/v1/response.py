from typing import Any, Literal
from pydantic import Field
from .request import APIModel
class ErrorResponse(APIModel):
    error_code: str
    message: str
    detail: dict | None = None
    request_id: str | None = None

class Metrics(APIModel):
    original_size: int = Field(ge=0); compressed_size: int = Field(ge=0)
    original_size_human: str | None = None
    compressed_size_human: str | None = None
    reduction_percent: float = Field(ge=-100, le=100); ssim: float = Field(ge=0, le=1)
    psnr: float = Field(ge=0); processing_time_seconds: float = Field(ge=0)
    iterations: int = Field(ge=1); params_used: dict[str, Any] = Field(default_factory=dict)
class Job(APIModel):
    job_id: str = Field(min_length=1); status: Literal['queued','processing','done','failed']
    metrics: Metrics | None = None; download_url: str | None = None; error: str | None = None
class JobSubmission(APIModel):
    job_id: str = Field(min_length=1); status: Literal['queued','processing','done','failed']
class Health(APIModel):
    status: Literal['ok']; ffmpeg: bool; workers: int = Field(ge=1); chunk_size: int = Field(gt=0)
class AppConfig(APIModel):
    max_file_size: int = Field(gt=0); small_file_threshold: int = Field(gt=0)
    chunk_size: int = Field(gt=0); ssim_threshold: float = Field(ge=0, le=1)
class UploadCreated(APIModel):
    upload_id: str; chunk_count: int = Field(ge=1); chunk_size: int = Field(gt=0)

class Comparison(APIModel):
    ai: Metrics
    baseline: Metrics
