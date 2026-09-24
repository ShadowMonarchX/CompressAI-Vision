# CompressAI Vision

CompressAI Vision is an asynchronous FastAPI service and browser test bench for image compression. It analyzes image features, predicts encoding parameters, evaluates quality, and adjusts compression until the configured quality target is reached.

## Requirements

- Python 3.11+
- [`uv`](https://docs.astral.sh/uv/)
- FFmpeg for the video endpoint and health check

Install FFmpeg on macOS with `brew install ffmpeg`, then verify it with `ffmpeg -version`.

## Run locally

```bash
uv sync
uv run uvicorn app.main:app --reload
```

Or use the development entrypoint:

```bash
uv run python scripts/run.py
```

Open <http://localhost:8000/static/test.html> for the browser test bench or <http://localhost:8000/docs> for API documentation.

## Browser UI

The static UI supports image/video selection, drag-and-drop uploads, previews, API/FFmpeg status, job polling, and downloads. Completed image jobs display the before-compression size, after-compression size, and percentage of size reduced. It uses plain HTML, CSS, and JavaScript with no frontend build step.

## API

All active endpoints use the `/api/v1` prefix.

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/compress/image` | Queue image compression; multipart field: `file` |
| POST | `/api/v1/compress/video` | Check FFmpeg and queue a video job |
| POST | `/api/v1/compare/image` | Compare adaptive compression with a fixed-quality baseline |
| GET | `/api/v1/jobs/{job_id}` | Read job status and compression metrics |
| GET | `/api/v1/jobs/{job_id}/download` | Download a completed result |
| GET | `/api/v1/health` | Read API, FFmpeg, worker, and chunk status |
| GET | `/api/v1/config` | Read client-safe size and quality limits |

Example:

```bash
curl -F file=@photo.png http://localhost:8000/api/v1/compress/image
curl http://localhost:8000/api/v1/jobs/<job_id>
curl -o compressed.jpg http://localhost:8000/api/v1/jobs/<job_id>/download
```

Submission returns `202` with `{"job_id":"...","status":"queued"}`. If FFmpeg is unavailable, the video endpoint returns `503 Service Unavailable`. The current background worker is image-oriented; full video transcoding is planned work.

## Configuration

Copy `.env.example` to `.env`:

```env
WORK_DIR=.work
CREATE_WORK_DIR=true
MAX_FILE_SIZE=524288000
CHUNK_SIZE=5242880
SSIM_THRESHOLD=0.90
MAX_ITERATIONS=3
RATE_LIMIT_PER_MINUTE=30
FFMPEG_BINARY=ffmpeg
```

`API_KEY` is optional. When set, requests must include an `X-API-Key` header. This is a minimal starting point; JWT/OAuth is the future upgrade path.

Set `CREATE_WORK_DIR=false` to prevent startup from creating the configured work directory. Upload and compression operations require that directory to exist, so leave it set to `true` for normal local use.

## Project structure

```text
app/
├── main.py                       # FastAPI application and static files
├── deps.py                       # Shared dependency providers
├── core/                         # Settings, security, logging, exceptions, algorithms
├── router/                       # Top-level and versioned routers
│   ├── v1/endpoints/             # Health, compression, jobs, upload, compare
│   └── v2/                       # Reserved, inactive API version
├── models/v1/                    # Versioned request and response models
├── models/v2/                    # Reserved v2 model modules
├── services/                     # AI orchestration, jobs, storage, and cache
└── utils/helpers.py              # Shared utility functions
static/                           # Browser test bench
scripts/run.py                    # Development entrypoint
```

The dependency direction is `router → services → core`. Core compression modules are callable without HTTP, job, or storage types. `AIService` owns feature extraction, prediction, encoding, quality evaluation, and the adjustment loop.

## API versioning

V1 is active. V2 has a wired but empty router and is excluded from OpenAPI until functionality is added. To add v2, create endpoint modules under `app/router/v2/endpoints`, register them in `app/router/v2/router.py`, and add matching models under `app/models/v2`.

## Checks

```bash
UV_CACHE_DIR=/tmp/compressai-uv-cache uv run python -m compileall -q app
node --check static/js/app.js
uv run pytest
```

### Development

Install the development tools with `uv sync --dev`. Run `uv run ruff format .`,
`uv run ruff check .`, and `uv run mypy app/` before submitting changes.
Install the repository hooks once with `uv run pre-commit install`.

The test suite includes an architecture regression test for the router → services → core boundary.

## Current limitations

- Jobs and cache are in memory; use Redis or a durable queue for multi-process deployments.
- Uploaded files are stored locally; use object storage such as S3 for production.
- Video availability is checked through FFmpeg, but the worker currently performs image compression.
- Authentication is optional API-key protection; upgrade to JWT/OAuth when needed.
- Rate limiting is configured but not yet enforced by middleware.
