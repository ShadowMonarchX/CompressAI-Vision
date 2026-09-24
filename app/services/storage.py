"""Local upload persistence boundary.

This module owns upload validation and bounded streaming. It deliberately
returns a filesystem path so the AI services remain independent of FastAPI's
``UploadFile`` after the request has been accepted.
"""

import uuid
from pathlib import Path

from app.core.exceptions import FileTooLargeError, MediaTypeError, ServiceUnavailableError

ALLOWED = {"image/jpeg", "image/png", "image/webp", "video/mp4", "video/webm", "video/quicktime"}
CHUNK_SIZE = 1024 * 1024


async def save_upload(file, settings) -> Path:
    """Validate and stream an upload into an isolated job directory."""
    if file.content_type not in ALLOWED:
        raise MediaTypeError("Unsupported media type")
    if not settings.work_dir.is_dir():
        raise ServiceUnavailableError(
            f"Work directory is unavailable: {settings.work_dir}. "
            "Set CREATE_WORK_DIR=true or create it manually."
        )

    folder = settings.work_dir / uuid.uuid4().hex
    folder.mkdir()
    filename = Path(file.filename or "upload").name
    destination = folder / filename
    total = 0
    try:
        with destination.open("wb") as output:
            while chunk := await file.read(CHUNK_SIZE):
                total += len(chunk)
                if total > settings.max_file_size:
                    raise FileTooLargeError("File exceeds MAX_FILE_SIZE")
                output.write(chunk)
        return destination
    except Exception:
        # Do not leave a partial upload that could be mistaken for a valid job.
        destination.unlink(missing_ok=True)
        folder.rmdir()
        raise
