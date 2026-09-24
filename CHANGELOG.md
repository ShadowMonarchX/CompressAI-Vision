# Changelog

## 0.1.0

- Initial async image compression API and resumable upload flow.
# Unreleased

- Full frontend rebuild (2026-09-24): recreated the static test bench from clean files with native hidden state, cache-busted assets, live configuration hints, upload progress, responsive styling, and dependency-free charts.

- Fixed the hidden-state bug in the static test bench by using the native `hidden` attribute consistently; removed conflicting `hidden` classes and synchronized tab/panel and upload-state visibility through the DOM property.
- Fixed the static test bench rendering path and upload-tab behavior: the FastAPI `/static` mount now matches the HTML asset URLs, and inactive Image/Video upload panels are hidden. Added styled comparison-endpoint errors and explicit upload-panel controls.

- Rebuilt the offline static test bench with image/video tabs, previews, resumable-upload progress, job stepper, before/after media, responsive canvas charts, download handling, and visible errors.
- Added `/api/v1/config` for UI thresholds and upload settings.
- Fixed static asset rendering by mounting the complete `static/` directory at `/static`; CSS and ES module assets now resolve instead of returning 404.
- Added typed compressor, feature-extractor, predictor, evaluator, and guarded job-state abstractions.
- Added ORJSON response support and streamed resumable chunk writes with checksum and disk-space validation.
- Removed the video endpoint's explicit 501 response and added ffmpeg readiness validation.
- Added `AUDIT_REPORT.md` with evidence and remaining gaps.
- API restructuring (2026-09-24): introduced the `/api/v1` router aggregator, domain router modules, dependency injection boundaries, typed compression/job/system responses, domain-error handling, and an explicit services package.
