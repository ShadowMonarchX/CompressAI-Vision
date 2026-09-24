# CompressAI Vision audit

## 1. Core design — PARTIAL

- PASS: `BaseCompressor`, `ImageCompressor`, typed feature dataclasses, predictor strategy, injected `QualityEvaluator`, and guarded `JobRecord` transitions are in `app/core/image_compressor.py`, `app/core/feature_extraction.py`, `app/core/parameter_predictor.py`, `app/core/quality_evaluator.py`, and `app/services/jobs.py`.
- PARTIAL: `JobStore` is concurrency-safe in `app/services/jobs.py`, but uploads remain an in-memory adapter in `app/main.py`; a formal storage ABC is still outstanding.

## 2. Dependencies — PARTIAL

`pyproject.toml` uses FastAPI/Uvicorn for HTTP, python-multipart for form uploads, pydantic-settings for environment configuration, Pillow for image codecs, NumPy for vectorized quality math, aiofiles for future storage adapters, and orjson for fast JSON responses. `uvicorn[standard]` supplies optional high-performance loop/parser extras where supported. The environment could not complete `uv sync` because network access to PyPI was unavailable.

## 3. Video — PARTIAL

`POST /api/v1/compress/video` no longer returns 501 and checks ffmpeg readiness, but the current worker still routes submitted files through the image worker. A full async ffmpeg codec worker, timeout/adjustment loop, and video fixture test remain required.

## 4. Scalability — PARTIAL

Image work is offloaded with `asyncio.to_thread` in `app/core/image_compressor.py`; `JobStore` uses an async lock. Per-client rate limiting, configurable CPU pools, and load-test results are not yet implemented.

## 5. Chunked uploads — PASS/PARTIAL

`app/main.py` streams request chunks directly to preallocated disk offsets, exposes resumable status, validates optional SHA-256 checksums, enforces declared/actual size, checks free disk space, and uses `FileResponse` for downloads. The large-file memory test is not yet included.

## 6. UI — FAIL

`static/test.html` remains a minimal direct-image demo; drag/drop, chunk routing, metrics, comparison, and visible progress/error handling still need implementation.

## 7. Verification — PARTIAL

`python -m compileall app` succeeds. Import and full pytest/health/video integration verification could not be completed because dependency resolution was blocked by unavailable network access. The 501 route gap is closed at the HTTP surface, but the complete video worker is not yet proven.
