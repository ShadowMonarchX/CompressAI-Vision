import asyncio, time, uuid
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from app.config import settings
from app.core.image_compressor import ImageCompressor

class JobState(str, Enum): QUEUED="queued"; PROCESSING="processing"; DONE="done"; FAILED="failed"
@dataclass
class JobRecord:
    job_id: str; source: Path; status: JobState = JobState.QUEUED; output: Path|None = None; metrics: dict|None = None; error: str|None = None
    def transition(self, state):
        allowed={JobState.QUEUED:{JobState.PROCESSING,JobState.FAILED},JobState.PROCESSING:{JobState.DONE,JobState.FAILED},JobState.DONE:set(),JobState.FAILED:set()}
        if state not in allowed[self.status]: raise ValueError(f"invalid transition {self.status}->{state}")
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
        score, params, iterations = await ImageCompressor(max_iterations=settings.max_iterations).compress(job.source,out)
        size=job.source.stat().st_size; out_size=out.stat().st_size
        job.output=out; job.metrics={"original_size":size,"compressed_size":out_size,"reduction_percent":round((1-out_size/size)*100,2),**score,"processing_time_seconds":round(time.perf_counter()-started,4),"iterations":iterations,"params_used":params}; job.transition(JobState.DONE)
    except Exception as exc: job.error=str(exc); job.transition(JobState.FAILED)
async def create_job(source):
    job=JobRecord(uuid.uuid4().hex,source); await jobs.add(job); asyncio.create_task(run_image(job)); return job.job_id
