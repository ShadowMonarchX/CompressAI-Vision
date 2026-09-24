import uuid
from pathlib import Path
from app.core.exceptions import FileTooLargeError, MediaTypeError
ALLOWED={"image/jpeg","image/png","image/webp","video/mp4","video/webm","video/quicktime"}
async def save_upload(file, settings):
    if file.content_type not in ALLOWED: raise MediaTypeError("Unsupported media type")
    folder=settings.work_dir/uuid.uuid4().hex; folder.mkdir(); path=folder/Path(file.filename or "upload").name; total=0
    with path.open("wb") as out:
        while chunk:=await file.read(1024*1024):
            total += len(chunk)
            if total > settings.max_file_size: raise FileTooLargeError("File exceeds MAX_FILE_SIZE")
            out.write(chunk)
    return path
