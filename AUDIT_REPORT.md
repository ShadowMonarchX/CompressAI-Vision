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

## 6. UI — PARTIAL

Root cause of the original unstyled screenshot: the app previously had a one-off `/static/test.html` route but no `/static` `StaticFiles` mount, so `/static/css/test.css` and `/static/js/app.js` returned 404. The mount is now present, uses an absolute repository-relative `Path`, and matches the HTML URLs. The canonical layout is `static/test.html`, `static/css/test.css`, and `static/js/{app,charts}.js`.

HTTP verification against a running Uvicorn server on 2026-09-24: `/static/test.html` returned 200 (`text/html`), `/static/css/test.css` returned 200 (`text/css`), and `/static/js/app.js` plus `/static/js/charts.js` returned 200 (`text/javascript`). The upload UI source includes separate Image/Video panels with real tab visibility toggling, styled previews/progress/cards, responsive charts, and an honest inline comparison-endpoint error.

Visual verification is not complete: no Chromium, Playwright, Puppeteer, or Selenium executable/package is installed in this environment, and therefore no headless screenshot or six-state browser report can be honestly claimed. Syntax checks are not treated as visual evidence. The backend `/api/v1/compare` route is still absent.

## 7. Verification — PARTIAL

`python -m compileall app` succeeds; `node --check` passes for both UI modules. Browser/manual verification was not executable in this environment. The 501 route gap is closed at the HTTP surface, but the complete video worker and compare flow are not yet proven.

## 8. Static directory deep audit — FAIL/PARTIAL

Audit scope: every file under `static/` as of 2026-09-24.

### Inventory and dependency map

| File | Size | Referenced by | Finding |
|---|---:|---|---|
| `static/test.html` | 8,054 B | `app/main.py`; loads `css/test.css` and `js/app.js` | Canonical page; no duplicate file found |
| `static/css/test.css` | 14,580 B | `test.html` | Canonical stylesheet; no duplicate file found |
| `static/js/app.js` | 23,155 B | `test.html` | Main controller; contains a critical startup token and several data-safety issues |
| `static/js/charts.js` | 7,788 B | imported by `app.js` | Chart module; no duplicate file found |

There are no additional files, hidden duplicate assets, nested build outputs, or duplicate directories in `static/`. SHA-1 checksums are unique across the four files. `test.html` appearing twice in a shell glob was the same path, not a second copy.

### Critical defect

- `static/js/app.js:1` contains the bare token `javascript` before the import declaration. `node --check` accepts it as syntactically valid JavaScript, but module evaluation raises `ReferenceError: javascript is not defined`; consequently imports, event bindings, configuration loading, and the complete UI stop before startup. Remove that line. This is the highest-priority fix.

### High-priority functional issues

- `static/js/app.js:1079-1100`: `info()` accepts only `[label, value]`, while the comparison table passes three-element rows (`Metric`, fixed, AI). The third value is silently discarded, so the “AI vs baseline” table cannot show both result columns. Change the renderer to support a real table or render separate columns explicitly.
- `static/js/app.js:1046-1065`: the comparison request is `POST /api/v1/compare` with no job ID, file, or comparison payload. Unless the backend derives the last job from server-side session state, this cannot identify what to compare. The current report already records that the backend route is absent.
- `static/js/app.js:258-265`: cloning the original video element copies the `src`, but image/video metadata handlers are not copied. The comparison preview is therefore less reliably initialized than the primary preview, especially for video metadata and error reporting.
- `static/js/app.js:350`: resumable-upload localStorage keys contain filename and size but not API base, file identity/hash, or modification time. A same-name/same-size different file can resume against the wrong upload session; changing API endpoints can also reuse an unrelated session ID.

### Security and robustness issues

- `static/js/app.js:108-124`, `207-211`, `674-709`, and `1079-1100`: `info()` builds `innerHTML` from file names and API-returned values without escaping. A crafted filename or compromised/malicious API response can inject markup/script into the page. Use `textContent` DOM nodes or an HTML escaping function for every displayed value.
- `static/js/app.js:315-348`: invalid or missing `small_file_threshold` falls through to chunked upload, which may be acceptable, but there is no upper-bound validation for API-provided `chunk_size`; an extreme value can cause unusable memory/request behavior. Validate finite integer limits client-side and rely on matching server validation.
- `static/js/app.js:648-653`, `711-713`: `base()` concatenates arbitrary localStorage/user input with API-provided paths. Restrict the API base to an allowed `http(s)` origin or same-origin path, and resolve URLs with `new URL()` to avoid malformed or unexpected destinations.
- `static/js/app.js:1129`: initial `loadConfig().catch(err)` reports an error but leaves upload controls active; the user can select a file and receive a second configuration error. Disable upload controls until configuration succeeds or provide an explicit unavailable state.
- `static/js/charts.js:423-467`: comparison chart values are clamped only by `drawBarChart`'s non-negative conversion, not by a meaningful percentage range. Invalid reductions above 100% or non-finite values can produce misleading chart scaling.
- `static/js/charts.js:295-300`: quality chart uses fixed left/right margins; at very narrow canvas widths, labels and bars can overlap. The responsive CSS stacks charts but does not change the canvas drawing margins.
- `static/js/charts.js:1-417`: charts are drawn once and are not redrawn on resize or device-pixel-ratio changes. Resizing the viewport can leave stale dimensions or blurry charts.

### Duplication review

- No byte-identical duplicate files exist.
- Repeated HTML classes (`card`, `media`, `muted`, `drop`, `error`, etc.) are intentional shared component classes, not duplicate components.
- `before`, `afterBefore`, and `after` are separate containers for distinct workflow states; however, the preview-building logic is duplicated conceptually and would be safer as a reusable media-element factory.
- Formatting patterns are highly repetitive in both JavaScript files (multi-line single expressions and repeated DOM hide/show pairs), but this is maintainability duplication rather than a duplicate asset. Small helpers such as `show(element)`/`hide(element)` and `setText()` would reduce it.

### Accessibility and compatibility

- `test.html:292-299` renders the download control as an anchor with `href="#"` until completion; it should be disabled/hidden until a valid URL exists to avoid a confusing no-op navigation.
- Canvas charts have labels but no textual data fallback. Users who cannot perceive canvas content do not receive equivalent values from the chart itself; the stats/table should be the authoritative accessible alternative and should remain visible near each chart.
- The CSS uses `:has()` at `static/css/test.css:866`. Modern browsers support it, but older embedded browsers may ignore that mobile padding rule. A class-based fallback would be safer if legacy support matters.
- The page depends on Google Fonts at `test.html:10-14`; offline deployments fall back to system fonts, which is functional but changes visual metrics.

### Recommended repair order

1. Delete `static/js/app.js:1` (`javascript`) and rerun a browser smoke test.
2. Replace unsafe `innerHTML` rendering with escaped/text-based DOM rendering; fix the three-column comparison table.
3. Make comparison requests carry the current job/file identity and implement/verify the backend endpoint.
4. Harden resumable-upload identity and API URL validation.
5. Add browser tests for initialization, image/video switching, upload failure/retry, result rendering, and comparison rendering; add chart resize coverage.
# API restructuring pass (2026-09-24)

The API entrypoint now contains application setup, middleware/static mounting, the shared domain exception handler, and one versioned-router include; route handlers moved into `app/api/v1/routers/`. Compression, job, and system routes use explicit response models and status codes, and upload persistence begins behind `app/services/storage.py`. `app/services/__init__.py` was added. `main.py` contains zero `@app.` route decorators (verified with ripgrep).

Endpoint mapping preserved: `POST /api/v1/compress/image` → same; `POST /api/v1/compress/video` → same; `GET /api/v1/jobs/{id}` → same; `GET /api/v1/jobs/{id}/download` → same; `GET /api/v1/health` → same; `GET /api/v1/config` → same. The upload router namespace is present, but its former resumable handlers still require migration into the storage service before this restructuring is complete.

Verification: `python -m compileall -q app` passes. Runtime import and pytest could not run because `fastapi` is unavailable in the environment; `uv` could not initialize its cache due to permissions. The checked-out workspace also has no `static/` directory, so static mounting is guarded until those assets are restored.
