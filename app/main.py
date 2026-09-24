import asyncio, hashlib, math, mimetypes, shutil, uuid
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from app.config import settings
from app.schemas.models import UploadInit, UploadCreated, Job
from app.services.jobs import jobs, create_job

app = FastAPI(title="CompressAI Vision", version="1.0.0")
uploads: dict[str, dict] = {}

@app.get("/static/test.html", include_in_schema=False)
async def demo():
    return FileResponse(Path(__file__).resolve().parent.parent / "static" / "test.html", media_type="text/html")

def problem(status: int, detail: str): return JSONResponse({"type":"about:blank", "title":"Request failed", "status":status, "detail":detail}, status_code=status, media_type="application/problem+json")
@app.exception_handler(HTTPException)
async def errors(_: Request, exc: HTTPException): return problem(exc.status_code, str(exc.detail))

async def save_upload(file: UploadFile, suffix="") -> Path:
    if file.content_type not in {"image/jpeg","image/png","image/webp","video/mp4","video/webm","video/quicktime"}: raise HTTPException(415, "Unsupported media type")
    folder = settings.work_dir / uuid.uuid4().hex; folder.mkdir(); path = folder / (Path(file.filename or "upload").name + suffix)
    total = 0
    with path.open("wb") as out:
        while chunk := await file.read(1024*1024):
            total += len(chunk)
            if total > settings.max_file_size: raise HTTPException(413, "File exceeds MAX_FILE_SIZE")
            out.write(chunk)
    return path

async def submit(file: UploadFile):
    path = await save_upload(file); job = create_job(path); return {"job_id":job, "status":"queued"}

@app.post("/api/v1/compress/image", summary="Compress an image")
async def image(file: UploadFile = File(...)): return await submit(file)
@app.post("/api/v1/compress/video", summary="Compress a video")
async def video(file: UploadFile = File(...)):
    raise HTTPException(501, "Video pipeline requires the configured system ffmpeg integration")

@app.post("/api/v1/upload/init", response_model=UploadCreated)
async def upload_init(req: UploadInit):
    if req.total_size > settings.max_file_size: raise HTTPException(413, "File exceeds MAX_FILE_SIZE")
    uid=uuid.uuid4().hex; folder=settings.work_dir/uid; folder.mkdir(); path=folder/req.filename
    path.touch(); uploads[uid]={"path":path,"size":req.total_size,"chunk":req.chunk_size,"received":set()}
    return {"upload_id":uid,"chunk_count":math.ceil(req.total_size/req.chunk_size)}
@app.get("/api/v1/upload/status/{upload_id}")
async def upload_status(upload_id:str):
    u=uploads.get(upload_id)
    if not u: raise HTTPException(404,"Upload not found")
    return {"upload_id":upload_id,"received_chunks":sorted(u["received"])}
@app.post("/api/v1/upload/chunk/{upload_id}/{chunk_index}")
async def upload_chunk(upload_id:str, chunk_index:int, request:Request):
    u=uploads.get(upload_id)
    if not u: raise HTTPException(404,"Upload not found")
    data=await request.body(); offset=chunk_index*u["chunk"]
    if offset+len(data)>u["size"]: raise HTTPException(400,"Chunk exceeds declared size")
    with u["path"].open("r+b") as f: f.seek(offset); f.write(data)
    u["received"].add(chunk_index); return {"ack":True,"sha256":hashlib.sha256(data).hexdigest()}
@app.post("/api/v1/upload/complete/{upload_id}")
async def upload_complete(upload_id:str):
    u=uploads.get(upload_id); expected=math.ceil(u["size"]/u["chunk"]) if u else 0
    if not u: raise HTTPException(404,"Upload not found")
    if len(u["received"]) != expected: raise HTTPException(400,"Missing chunks")
    return {"job_id":create_job(u["path"]),"status":"queued"}
@app.get("/api/v1/jobs/{job_id}", response_model=Job)
async def job(job_id:str):
    j=jobs.get(job_id)
    if not j: raise HTTPException(404,"Job not found")
    return {"job_id":job_id, **{k:v for k,v in j.items() if k in ("status","metrics","error")}, "download_url":f"/api/v1/jobs/{job_id}/download" if j["status"]=="done" else None}
@app.get("/api/v1/jobs/{job_id}/download")
async def download(job_id:str):
    j=jobs.get(job_id)
    if not j or j["status"]!="done": raise HTTPException(404,"Result not ready")
    return FileResponse(j["output"], media_type="image/jpeg", filename="compressed.jpg")
@app.get("/api/v1/health")
async def health(): return {"status":"ok","ffmpeg":bool(shutil.which(settings.ffmpeg_binary)),"workers":settings.max_workers or 1}
