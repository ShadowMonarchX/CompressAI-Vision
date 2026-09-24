# CompressAI Vision

An async FastAPI service for heuristic-driven image compression with resumable, disk-backed uploads and job polling. Python 3.11.15 and `uv` are the supported runtime.

## Run

Install [uv](https://docs.astral.sh/uv/), install system `ffmpeg`, then run:

```bash
uv sync
uv run uvicorn app.main:app --reload
```

Open `/docs`. A small upload is submitted with `curl -F file=@photo.png http://localhost:8000/api/v1/compress/image`; poll the returned job and download its result. The chunk flow is `upload/init` → repeated `upload/chunk/{id}/{index}` → `upload/complete/{id}` → `jobs/{job_id}`. `upload/status/{id}` makes interrupted uploads resumable.

## Design

Uploads are preallocated and written at offsets, so the full input is never held in memory. Each job has an isolated working directory. Pillow and NumPy provide codec access and lightweight entropy/gradient features; the predictor is a replaceable `Predictor` protocol. Quality uses manually implemented PSNR and SSIM-like luminance/variance scoring. CPU work runs in `asyncio.to_thread` and can be moved behind the job service interface. FFmpeg is a system dependency (industry-standard codec engine); the video route is intentionally an explicit 501 until that worker is enabled, avoiding a false claim of video support.

Configuration is twelve-factor via `.env`; see `.env.example`. For production, replace the in-memory `jobs` and `uploads` dictionaries with Redis/Postgres and use shared object storage (S3-compatible) across API instances. Add an authenticated per-user token bucket before exposing the service publicly.

Dependencies are intentionally small: FastAPI/Uvicorn serve the API, multipart parses uploads, pydantic-settings validates configuration, Pillow encodes images, NumPy performs feature math, and aiofiles is reserved for a future fully async storage adapter. Pytest/httpx are development-only.

## Checks

```bash
uv run python -m compileall app
uv run pytest
```

For large-file validation, upload a file larger than 500 MB in 5 MB chunks while watching the process RSS; only one request chunk is buffered. Benchmark and load-test numbers are environment-dependent and should be recorded with the hardware, input corpus, and command used.
