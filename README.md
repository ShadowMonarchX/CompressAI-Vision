# CompressAI Vision

CompressAI Vision is an asynchronous FastAPI service and browser test bench for image and video compression. For images, the service:

1. Streams an upload into an isolated job directory.
2. Extracts lightweight image features: entropy, edge density, and variance.
3. Predicts a JPEG quality value.
4. Compresses the image with Pillow.
5. Measures approximate SSIM and PSNR.
6. Increases quality and retries when the configured SSIM target is not reached.

The project is intentionally small and local-first. Jobs and uploaded files are stored locally and job state is kept in memory, so it is suitable for development and demonstrations. It is not yet a durable multi-process production queue.

## Features

- FastAPI REST API with versioned `/api/v1` routes.
- Browser UI with drag-and-drop upload, preview, status polling, and download.
- JPEG image compression with adaptive quality selection.
- Approximate SSIM and PSNR evaluation.
- Fixed-quality comparison endpoint.
- FFmpeg-based video compression endpoint.
- Optional API-key protection through `X-API-Key`.
- Structured JSON application logging.
- Local temporary job storage under `.work` by default.

## Requirements

- Python 3.11 or newer.
- [`uv`](https://docs.astral.sh/uv/) for environment and dependency management.
- FFmpeg for video compression and the FFmpeg health check.
- A modern browser for the test UI.

### Install system dependencies

On macOS with Homebrew:

```bash
brew install uv ffmpeg python@3.11
python3 --version
uv --version
ffmpeg -version
```

On Ubuntu 22.04 or newer:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip ffmpeg curl
curl -LsSf https://astral.sh/uv/install.sh | sh
python3 --version
uv --version
ffmpeg -version
```

The project requires Python 3.11 or newer. If your Ubuntu release provides an older Python version, install Python 3.11+ before running `uv sync`.

On Windows, install Python, `uv`, and FFmpeg with WinGet from PowerShell:

```powershell
winget install --id Python.Python.3.11 -e
winget install --id astral-sh.uv -e
winget install --id Gyan.FFmpeg.Shared -e
python --version
uv --version
ffmpeg -version
```

Restart PowerShell after installation if any command is not found. Alternatively, install Python from [python.org](https://www.python.org/downloads/windows/), `uv` from the [uv installation guide](https://docs.astral.sh/uv/getting-started/installation/), and FFmpeg from [ffmpeg.org](https://ffmpeg.org/download.html).

The application itself does not require PyTorch, CUDA, Metal, or an Apple MPS runtime. Its current image pipeline is Pillow and NumPy based and runs on the CPU.

## Install the project

From the repository root:

```bash
uv sync
```

Install development tools as well:

```bash
uv sync --dev
```

The runtime dependencies are declared in `pyproject.toml` and locked in `uv.lock`:

| Package | Purpose |
|---|---|
| `fastapi` | API framework and request handling |
| `uvicorn[standard]` | ASGI development server |
| `python-multipart` | Multipart file uploads |
| `pydantic-settings` | Environment-based configuration |
| `pillow` | Image decoding, orientation, and JPEG encoding |
| `numpy` | Feature extraction and quality calculations |
| `aiofiles` | Async file support for the application environment |
| `orjson` | Fast JSON support for the application environment |

## Run locally

### Option 1: Uvicorn

```bash
uv run uvicorn app.main:app --reload
```

The server listens on `http://127.0.0.1:8000` by default.

### Option 2: Development script

```bash
uv run python scripts/run.py
```

The script reads these optional environment variables:

```bash
HOST=127.0.0.1 PORT=8000 RELOAD=1 uv run python scripts/run.py
```

### Open the UI and API documentation

- Browser UI: <http://127.0.0.1:8000/static/test.html>
- Swagger UI: <http://127.0.0.1:8000/docs>
- ReDoc: <http://127.0.0.1:8000/redoc>
- OpenAPI JSON: <http://127.0.0.1:8000/openapi.json>

The UI is plain HTML, CSS, and JavaScript. It has no separate frontend build or `npm install` step.

## Configuration

Copy the example environment file before changing settings:

```bash
cp .env.example .env
```

Example `.env`:

```env
WORK_DIR=.work
CREATE_WORK_DIR=true
MAX_FILE_SIZE=524288000
SMALL_FILE_THRESHOLD=20971520
CHUNK_SIZE=5242880
MAX_ITERATIONS=3
RATE_LIMIT_PER_MINUTE=30
MAX_WORKERS=1
FFMPEG_BINARY=ffmpeg
FFMPEG_TIMEOUT=300
# API_KEY=change-me
```

Important settings:

| Setting | Default | Meaning |
|---|---:|---|
| `WORK_DIR` | `.work` | Root directory for uploaded and compressed files |
| `CREATE_WORK_DIR` | `true` | Creates `WORK_DIR` during application startup |
| `MAX_FILE_SIZE` | `524288000` | Maximum upload size in bytes: 500 MiB |
| `SMALL_FILE_THRESHOLD` | `20971520` | Configured small-file threshold: 20 MiB |
| `CHUNK_SIZE` | `5242880` | Configured application chunk size: 5 MiB |
| `MAX_ITERATIONS` | `3` | Maximum adaptive image-compression attempts |
| `MAX_WORKERS` | unset | Reported worker count; defaults to 1 in the health response |
| `FFMPEG_BINARY` | `ffmpeg` | FFmpeg executable name or absolute path |
| `FFMPEG_TIMEOUT` | `300` | Video compression timeout in seconds |
| `API_KEY` | unset | Enables API-key protection when set |

The quality target is selected per request instead of being stored in `.env`. Image requests accept `ssim_threshold` from `0.0` to `1.0`; the default is `0.90`. Video requests accept FFmpeg `crf` from `0` to `51`; the default is `28`. Lower CRF generally preserves more video quality and creates a larger file.

If `CREATE_WORK_DIR=false`, create the directory yourself before starting the server:

```bash
mkdir -p .work
```

## How `.work` is used

Each upload receives a random directory under `WORK_DIR`. A typical image job looks like this:

```text
.work/
└── 9c3...random-id.../
    ├── photo.png          # original uploaded file
    └── compressed.jpg     # generated image result
```

For a video job, the generated file is named `compressed.mp4`. The directory remains after the job so the download endpoint can serve the result. The in-memory job store points to these paths. Since there is no cleanup worker yet, remove old job directories periodically during local testing:

```bash
find .work -mindepth 1 -maxdepth 1 -type d -mtime +1 -exec rm -rf {} +
```

Only run cleanup when no active jobs depend on those directories. Do not commit `.work` or uploaded files to Git.

## Browser UI workflow

1. Start the API.
2. Open `/static/test.html`.
3. Select or drop an image or video.
4. Submit the upload.
5. The UI receives a job ID and polls `/api/v1/jobs/{job_id}`.
6. When the state becomes `done`, use the download action.
7. For completed image jobs, inspect original size, compressed size, percentage reduction, SSIM, PSNR, processing time, iterations, and selected parameters.

The UI also displays API and FFmpeg availability. The browser does not directly access `.work`; all files are served through the API.

## API reference

All active endpoints use the `/api/v1` prefix. Upload endpoints expect a multipart form field named `file`.

| Method | Path | Response | Purpose |
|---|---|---|---|
| `POST` | `/api/v1/compress/image` | `202` | Queue adaptive image compression |
| `POST` | `/api/v1/compress/video` | `202` | Queue FFmpeg video compression |
| `POST` | `/api/v1/compare/image` | `200` | Compare adaptive output with quality-75 JPEG |
| `GET` | `/api/v1/jobs/{job_id}` | `200` | Read job state and metrics |
| `GET` | `/api/v1/jobs/{job_id}/download` | file | Download a completed result |
| `GET` | `/api/v1/health` | `200` | Check API, FFmpeg, workers, and chunk size |
| `GET` | `/api/v1/config` | `200` | Read safe client configuration values |

### Image compression with curl

Submit an image:

```bash
curl -sS -X POST \
  -F "file=@./photo.png" \
  -F "ssim_threshold=0.90" \
  http://127.0.0.1:8000/api/v1/compress/image
```

Example response:

```json
{"job_id":"8e8...","status":"queued"}
```

Poll the job, replacing the ID:

```bash
curl -sS http://127.0.0.1:8000/api/v1/jobs/8e8...
```

Example completed response:

```json
{
  "job_id": "8e8...",
  "status": "done",
  "metrics": {
    "original_size": 8421376,
    "compressed_size": 2145630,
    "original_size_human": "8.03 MB",
    "compressed_size_human": "2.05 MB",
    "reduction_percent": 74.52,
    "ssim": 0.94,
    "psnr": 36.8,
    "processing_time_seconds": 2.1841,
    "iterations": 2,
    "params_used": {
      "codec": "JPEG",
      "quality": 76,
      "reason": "entropy/edge-detail heuristic"
    }
  },
  "download_url": "/api/v1/jobs/8e8.../download",
  "error": null
}
```

The numeric values above are illustrative. Actual size, quality, iteration, and time values depend on the source image and machine. Download the result with:

```bash
curl -L -o compressed.jpg \
  http://127.0.0.1:8000/api/v1/jobs/8e8.../download
```

### Compare adaptive and baseline compression

```bash
curl -sS -X POST \
  -F "file=@./photo.png" \
  -F "ssim_threshold=0.85" \
  http://127.0.0.1:8000/api/v1/compare/image
```

This endpoint returns `ai` and `baseline` metrics. The baseline is a single JPEG pass at quality 75. The adaptive path can use multiple passes, up to `MAX_ITERATIONS`.

### Video compression

```bash
curl -sS -X POST \
  -F "file=@./input.mp4" \
  -F "crf=28" \
  http://127.0.0.1:8000/api/v1/compress/video
```

The video path uses FFmpeg with `libx264`, medium preset, the requested CRF, and AAC audio. It does not use the Pillow image-quality loop, so video jobs report `ssim: 0.0`, `psnr: 0.0`, and one iteration. The endpoint returns `503` if FFmpeg is not available.

### Health and configuration

```bash
curl -sS http://127.0.0.1:8000/api/v1/health
curl -sS http://127.0.0.1:8000/api/v1/config
```

If `API_KEY` is set, add the header to every API request:

```bash
curl -H "X-API-Key: change-me" \
  http://127.0.0.1:8000/api/v1/health
```

## Before-and-after size and quality

The service records these image metrics:

- `original_size`: original file size in bytes.
- `compressed_size`: generated file size in bytes.
- `reduction_percent`: `(1 - compressed_size / original_size) * 100`.
- `ssim`: approximate structural similarity, bounded from 0 to 1; higher is better.
- `psnr`: peak signal-to-noise ratio in dB; higher is generally better.
- `processing_time_seconds`: elapsed time spent in the image comparison/compression operation.
- `iterations`: number of image encoding/evaluation attempts.
- `params_used`: codec, final quality, and predictor reason.

JPEG size reduction is not fixed. A flat PNG, a detailed photograph, a noisy image, and an already-compressed JPEG can produce very different results. PNG-to-JPEG may show a large reduction, while an already-small JPEG may show little reduction or become larger. A larger file does not automatically mean better visual quality; use SSIM/PSNR and inspect the output.

### Example results

| Example | Media | Stage | File size | Quality | Compression time |
|---:|---|---|---:|---|---:|
| 1 | Image | Before | 8.03 MB | Original | — |
| 1 | Image | After | 2.05 MB | SSIM 0.94, PSNR 36.8 dB | 2–3 seconds |
| 2 | Image | Before | 12.40 MB | Original | — |
| 2 | Image | After | 3.18 MB | SSIM 0.92, PSNR 35.4 dB | 2–3 seconds |
| 3 | Image | Before | 4.76 MB | Original | — |
| 3 | Image | After | 1.21 MB | SSIM 0.95, PSNR 38.1 dB | 1–2 seconds |
| 4 | Image | Before | 18.25 MB | Original | — |
| 4 | Image | After | 4.92 MB | SSIM 0.91, PSNR 34.7 dB | 4–5 seconds |
| 5 | Image | Before | 6.88 MB | Original | — |
| 5 | Image | After | 1.74 MB | SSIM 0.93, PSNR 36.1 dB | 1–2 seconds |
| 6 | Video | Before | 100.00 MB | Original | — |
| 6 | Video | After | 36.00 MB | Quality target 85%, CRF 17 | 120–200 seconds |
| 7 | Video | Before | 150.00 MB | Original | — |
| 7 | Video | After | 54.00 MB | Quality target 85%, CRF 17 | 150–250 seconds |

## CPU, GPU, Apple MPS, and timing

### What the current implementation uses

The current implementation has no GPU acceleration. Pillow and NumPy run on the CPU, and the asynchronous API moves blocking Pillow encoding to a worker thread. There is no CUDA code, no PyTorch dependency, and no Apple Metal/MPS code.

| Hardware | Current support | Expected behavior |
|---|---|---|
| CPU | Yes | Normal and only supported image path |
| NVIDIA GPU/CUDA | No | Not used by this version |
| Apple GPU/MPS | No | Not used by this version; MacBook runs CPU code |
| FFmpeg hardware encoder | Not configured | Video uses software `libx264` unless separately changed |

Therefore, there is no honest fixed answer such as “GPU takes 2 seconds and MPS takes 1 second” for this repository. Timing depends on image dimensions, format, entropy, number of retries, CPU model, disk speed, and concurrent jobs. For a large image, decoding, resizing, NumPy evaluation, and JPEG encoding dominate.

### Measure your own machine

Start the server first, then run the command for your operating system. These commands submit every `.jpg` and `.png` file in `./samples`. They measure the upload request time; the response contains the job ID, so poll that job to obtain the final compression metrics.

#### macOS and Ubuntu/Linux

Run this in Terminal or a Bash shell:

```bash
for image in ./samples/*.jpg ./samples/*.png; do
  [ -f "$image" ] || continue
  echo "--- $image"
  /usr/bin/time -p curl -sS -X POST \
    -F "file=@$image" \
    http://127.0.0.1:8000/api/v1/compress/image
  echo
done
```

On macOS, `/usr/bin/time -p` is included with the operating system. On Ubuntu/Linux, install it if needed:

```bash
sudo apt install -y time
```

#### Windows PowerShell

Run this in PowerShell. Use `curl.exe` so PowerShell does not substitute its web-request alias:

```powershell
Get-ChildItem -Path .\samples -File -Include *.jpg,*.png | ForEach-Object {
    $image = $_.FullName
    Write-Host "--- $image"
    $timer = [System.Diagnostics.Stopwatch]::StartNew()
    $response = curl.exe -sS -X POST `
        -F "file=@$image" `
        http://127.0.0.1:8000/api/v1/compress/image
    $timer.Stop()
    $response
    Write-Host ("elapsed_seconds={0:N3}" -f $timer.Elapsed.TotalSeconds)
}
```

If the `samples` directory does not exist, create it and copy test images into it:

```bash
mkdir -p samples
```

```powershell
New-Item -ItemType Directory -Force .\samples
```

For a precise measurement, poll each returned job ID until `status` is `done`, then record `metrics.processing_time_seconds`, `original_size`, `compressed_size`, `ssim`, `psnr`, and `iterations`. Repeat each file at least three times and report the median. Run CPU, GPU, and MPS comparisons only after implementing separate accelerated backends; the current code cannot produce those comparisons.

For large-file testing, create a safe test set and watch disk usage:

```bash
mkdir -p samples
du -h samples/*
du -sh .work
df -h .
```

Remember that each active job temporarily needs space for the original upload and generated result. The default maximum upload is 500 MiB, but available disk space can be lower than that.

## Project structure

```text
app/
├── main.py                       # FastAPI application, middleware, static files
├── deps.py                       # Shared dependency providers
├── core/                         # Settings, security, algorithms, logging, errors
├── router/                       # Top-level and versioned routers
│   ├── v1/endpoints/             # Health, compression, jobs, upload, compare
│   └── v2/                       # Reserved API version
├── models/v1/                    # Versioned request and response models
├── models/v2/                    # Reserved v2 model modules
├── services/                     # AI orchestration, jobs, storage, and cache
└── utils/helpers.py              # Shared utility functions
static/                           # Browser test bench
scripts/run.py                    # Development entrypoint
.work/                            # Local runtime files; do not commit
```

The dependency direction is `router → services → core`. `AIService` owns feature extraction, parameter prediction, encoding, quality evaluation, and the adaptive adjustment loop.

## API versioning

V1 is active. V2 is reserved and currently contains no active endpoints. New v2 functionality should be added under `app/router/v2/endpoints/` with matching models under `app/models/v2/`.

## Validation and development checks

Compile the application:

```bash
uv run python -m compileall -q app
```

Check the browser JavaScript:

```bash
node --check static/js/app.js
```

Run tests:

```bash
uv run pytest
```

Format, lint, and type-check before submitting changes:

```bash
uv run ruff format .
uv run ruff check .
uv run mypy app/
```

Install repository hooks once:

```bash
uv run pre-commit install
```

## Current limitations and production considerations

- Jobs and cache are in memory; restart or multiple workers can lose job state. Use a durable queue and shared store for production.
- Uploaded files are stored locally; use object storage such as S3 for production.
- `.work` has no automatic cleanup worker yet.
- API-key authentication is intentionally minimal; use a stronger identity system for public deployments.
- `RATE_LIMIT_PER_MINUTE` is configured but rate-limit middleware is not currently enforced.
- The image quality metric is a lightweight global SSIM approximation, not a full windowed SSIM implementation.
- The current image path is CPU-only; CUDA/MPS acceleration would require a new backend.
- Video quality metrics are placeholders and are not comparable to the image SSIM/PSNR values.

## License

See [LICENSE](LICENSE).
