"""Synchronous image comparison endpoint."""

import time
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi import APIRouter, File, UploadFile

from app.core.config import settings
from app.models.v1.response import Comparison
from app.services.ai_service import AIService
from app.services.storage import save_upload

router = APIRouter(prefix="/compare", tags=["compare"])


def _metrics(source: Path, output: Path, result: tuple, elapsed: float) -> dict:
    """Translate service results into the public comparison metric shape."""
    score, params, iterations = result
    original_size, compressed_size = source.stat().st_size, output.stat().st_size
    return {
        "original_size": original_size,
        "compressed_size": compressed_size,
        "original_size_human": None,
        "compressed_size_human": None,
        "reduction_percent": round((1 - compressed_size / original_size) * 100, 2),
        **score,
        "processing_time_seconds": round(elapsed, 4),
        "iterations": iterations,
        "params_used": params,
    }


@router.post("/image", response_model=Comparison)
async def compare_image(file: UploadFile = File(...)):
    """Compare adaptive and fixed-quality JPEG outputs for one image."""
    source = await save_upload(file, settings)
    with TemporaryDirectory(dir=settings.work_dir) as directory:
        root = Path(directory)
        started = time.perf_counter()
        ai_result, baseline_result = await AIService().compare_image(
            source, root / "ai.jpg", root / "baseline.jpg"
        )
        elapsed = time.perf_counter() - started
        return {
            "ai": _metrics(source, root / "ai.jpg", ai_result, elapsed),
            "baseline": _metrics(source, root / "baseline.jpg", baseline_result, elapsed),
        }
