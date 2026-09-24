# CompressAI Vision

Async FastAPI service and responsive browser test bench for intelligent image/video compression.

## Run locally

Requirements: Python 3.11+, `uv`, and `ffmpeg`.

```bash
uv sync
uv run uvicorn app.main:app --reload
```

Open the UI at http://localhost:8000/static/test.html or API docs at http://localhost:8000/docs.

## Browser UI

```text
static/
├── test.html
├── css/test.css
└── js/app.js
```

The UI provides image/video tabs, drag-and-drop selection, previews, API and FFmpeg status, compression progress, job polling, reduction results, and downloads. It uses the same-origin API and needs no frontend build step.

## API reference

All endpoints use the `/api/v1` prefix and appear grouped in `/docs`.

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/compress/image` | Queue image compression; multipart field: `file` |
| POST | `/api/v1/compress/video` | Check FFmpeg and queue video job |
| POST | `/api/v1/upload/init` | Begin resumable upload |
| POST | `/api/v1/upload/chunk/{upload_id}/{chunk_index}` | Send one chunk |
| POST | `/api/v1/upload/complete/{upload_id}` | Complete upload |
| GET | `/api/v1/upload/status/{upload_id}` | Read received chunks |
| GET | `/api/v1/jobs/{job_id}` | Read job status and metrics |
| GET | `/api/v1/jobs/{job_id}/download` | Download completed result |
| GET | `/api/v1/health` | Read service readiness |
| GET | `/api/v1/config` | Read UI limits |
| POST | `/api/v1/compare/image` | Compare adaptive compression with a fixed-quality baseline |

Example:

```bash
curl -F file=@photo.png http://localhost:8000/api/v1/compress/image
curl http://localhost:8000/api/v1/jobs/<job_id>
curl -o compressed.jpg http://localhost:8000/api/v1/jobs/<job_id>/download
```

Submission returns `202` and `{"job_id":"...","status":"queued"}`.

## Project structure

```text
app/
├── main.py                 # FastAPI setup, errors, static mount
├── deps.py                 # injectable dependencies
├── router/                 # top-level, versioned routers (v1 active, v2 reserved)
├── core/                   # settings, logging, security, and compression algorithms
├── models/v1/               # split request and response Pydantic models
└── services/                # AI orchestration, jobs, storage, and cache boundaries
```

To add v2, add endpoint modules under `app/router/v2/endpoints`, include them from `app/router/v2/router.py`, and add versioned models under `app/models/v2`. The reserved v2 router is currently excluded from OpenAPI and has no routes.

Compression algorithms remain in `core/` (including the deliberate extension `exceptions.py`); `services/ai_service.py` owns orchestration and business rules. This keeps model logic separate from external integration. Authentication starts with an optional API-key header (`API_KEY`), with JWT/OAuth as the future upgrade path. `services/cache_service.py` provides a TTL in-memory cache, designed to be replaced by Redis when persistence or multi-process sharing is needed.

## Configuration

Settings come from environment variables or `.env`: `WORK_DIR` defaults to `.work`, `MAX_FILE_SIZE` to 524288000 bytes, `CHUNK_SIZE` to 5242880 bytes, `MAX_ITERATIONS` to 3, `SSIM_THRESHOLD` to 0.90, and `FFMPEG_BINARY` to `ffmpeg`.

## Checks

```bash
python -m compileall -q app
node --check static/js/app.js
uv run pytest
```

Compression runs away from the request path with `asyncio.to_thread`; job state uses an async lock. For production, replace in-memory jobs and local files with Redis/Postgres and S3-compatible storage.

## Known limitations

This is a local test bench. Video readiness is checked through FFmpeg, while the current worker is primarily image-oriented. The upload namespace is prepared for resumable storage integration. Authentication, rate limiting, durable queues, and browser automation tests are not included.
