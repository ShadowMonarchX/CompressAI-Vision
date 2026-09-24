import asyncio, time, uuid
from pathlib import Path
from app.config import settings
from app.core.image_compressor import compress

jobs: dict[str, dict] = {}

async def run_image(job_id: str, source: Path):
    out = source.parent / "compressed.jpg"; jobs[job_id]["status"] = "processing"; started = time.perf_counter()
    try:
        score, params = await asyncio.to_thread(compress, source, out, settings.max_iterations, settings.ssim_threshold)
        jobs[job_id].update(status="done", output=out, metrics={"original_size": source.stat().st_size, "compressed_size": out.stat().st_size,
          "reduction_percent": round((1-out.stat().st_size/source.stat().st_size)*100, 2), **score,
          "processing_time_seconds": round(time.perf_counter()-started, 4), "iterations": 1, "params_used": params})
    except Exception as exc: jobs[job_id].update(status="failed", error=str(exc))

def create_job(source: Path) -> str:
    job_id = uuid.uuid4().hex; jobs[job_id] = {"status":"queued", "source":source}; asyncio.create_task(run_image(job_id, source)); return job_id
