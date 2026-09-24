import asyncio, time, uuid
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from app.core.config import settings
from app.services.ai_service import AIService
from app.core.exceptions import InvalidJobStateTransitionError
from app.utils.helpers import format_size

class JobState(str, Enum): QUEUED="queued"; PROCESSING="processing"; DONE="done"; FAILED="failed"
@dataclass
class JobRecord:
    job_id: str; source: Path; media_type: str = "image"; status: JobState = JobState.QUEUED; output: Path|None = None; metrics: dict|None = None; error: str|None = None
    def transition(self, state):
        allowed={JobState.QUEUED:{JobState.PROCESSING,JobState.FAILED},JobState.PROCESSING:{JobState.DONE,JobState.FAILED},JobState.DONE:set(),JobState.FAILED:set()}
        if state not in allowed[self.status]:
            raise InvalidJobStateTransitionError(f"Invalid job transition {self.status}->{state}")
        self.status=state
class JobStore:
    def __init__(self): self._jobs={}; self._lock=asyncio.Lock()
    async def add(self, job):
        async with self._lock: self._jobs[job.job_id]=job
    async def get(self, job_id):
        async with self._lock: return self._jobs.get(job_id)
jobs=JobStore()
async def run_image(job):
    job.transition(JobState.PROCESSING); started=time.perf_counter(); out=job.source.parent/"compressed.jpg"
    try:
        score, params, iterations = await AIService().compress_image(job.source, out)
        size=job.source.stat().st_size; out_size=out.stat().st_size
        job.output=out; job.metrics={"original_size":size,"compressed_size":out_size,"original_size_human":format_size(size),"compressed_size_human":format_size(out_size),"reduction_percent":round((1-out_size/size)*100,2),**score,"processing_time_seconds":round(time.perf_counter()-started,4),"iterations":iterations,"params_used":params}; job.transition(JobState.DONE)
    except Exception as exc: job.error=str(exc); job.transition(JobState.FAILED)
async def run_video(job):
    job.transition(JobState.PROCESSING); started=time.perf_counter(); out=job.source.parent/"compressed.mp4"
    try:
        params = await AIService().compress_video(job.source, out)
        size, out_size = job.source.stat().st_size, out.stat().st_size
        job.output=out; job.metrics={"original_size":size,"compressed_size":out_size,"original_size_human":format_size(size),"compressed_size_human":format_size(out_size),"reduction_percent":round((1-out_size/size)*100,2),"ssim":0.0,"psnr":0.0,"processing_time_seconds":round(time.perf_counter()-started,4),"iterations":1,"params_used":params}; job.transition(JobState.DONE)
    except Exception as exc: job.error=str(exc); job.transition(JobState.FAILED)
async def create_job(source, media_type="image"):
    job=JobRecord(uuid.uuid4().hex,source,media_type=media_type); await jobs.add(job)
    asyncio.create_task(run_video(job) if media_type == "video" else run_image(job)); return job.job_id
