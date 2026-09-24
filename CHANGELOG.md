# Changelog

## 0.1.0

- Initial async image compression API and resumable upload flow.
# Unreleased

- Added typed compressor, feature-extractor, predictor, evaluator, and guarded job-state abstractions.
- Added ORJSON response support and streamed resumable chunk writes with checksum and disk-space validation.
- Removed the video endpoint's explicit 501 response and added ffmpeg readiness validation.
- Added `AUDIT_REPORT.md` with evidence and remaining gaps.
