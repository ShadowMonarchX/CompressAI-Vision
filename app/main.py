import hashlib, math, shutil, uuid
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, ORJSONResponse, StreamingResponse
from app.config import settings
from app.services.jobs import jobs, create_job

app=FastAPI(title="CompressAI Vision",version="1.0.0",default_response_class=ORJSONResponse)
app.mount("/static", StaticFiles(directory=Path(__file__).resolve().parent.parent / "static"), name="static")
uploads={}
ALLOWED={"image/jpeg","image/png","image/webp","video/mp4","video/webm","video/quicktime"}
async def save_upload(file):
    if file.content_type not in ALLOWED: raise HTTPException(415,"Unsupported media type")
    folder=settings.work_dir/uuid.uuid4().hex; folder.mkdir(); path=folder/Path(file.filename or "upload").name; total=0
    with path.open("wb") as out:
        while chunk:=await file.read(1024*1024):
            total+=len(chunk)
            if total>settings.max_file_size: raise HTTPException(413,"File exceeds MAX_FILE_SIZE")
            out.write(chunk)
    return path
@app.get("/static/test.html",include_in_schema=False)
async def demo(): return FileResponse(Path(__file__).resolve().parent.parent/"static/test.html")
async def submit(file): return {"job_id":await create_job(await save_upload(file)),"status":"queued"}
@app.post("/api/v1/compress/image")
async def image(file:UploadFile=File(...)): return await submit(file)
@app.post("/api/v1/compress/video")
async def video(file:UploadFile=File(...)):
    if not shutil.which(settings.ffmpeg_binary): raise HTTPException(503,"ffmpeg is unavailable")
    return await submit(file)
@app.post("/api/v1/upload/init")
async def upload_init(req:dict):
    size=int(req["total_size"]); chunk=int(req.get("chunk_size",settings.chunk_size))
    if size>settings.max_file_size: raise HTTPException(413,"File exceeds MAX_FILE_SIZE")
    if shutil.disk_usage(settings.work_dir).free<size: raise HTTPException(507,"Insufficient disk space")
    uid=uuid.uuid4().hex; folder=settings.work_dir/uid; folder.mkdir(); path=folder/Path(req["filename"]).name; path.touch(); uploads[uid]={"path":path,"size":size,"chunk":chunk,"received":{}}
    return {"upload_id":uid,"chunk_count":math.ceil(size/chunk),"chunk_size":chunk}
@app.get("/api/v1/upload/status/{upload_id}")
async def upload_status(upload_id:str):
    u=uploads.get(upload_id)
    if not u: raise HTTPException(404,"Upload not found")
    return {"upload_id":upload_id,"received_chunks":sorted(u["received"])}
@app.post("/api/v1/upload/chunk/{upload_id}/{chunk_index}")
async def upload_chunk(upload_id:str,chunk_index:int,request:Request,checksum:str|None=None):
    u=uploads.get(upload_id)
    if not u: raise HTTPException(404,"Upload not found")
    offset=chunk_index*u["chunk"]; written=0; digest=hashlib.sha256()
    with u["path"].open("r+b") as out:
        out.seek(offset)
        async for data in request.stream():
            written+=len(data); digest.update(data)
            if offset+written>u["size"]: raise HTTPException(400,"Chunk exceeds declared size")
            out.write(data)
    actual=digest.hexdigest()
    if checksum and checksum!=actual: raise HTTPException(400,"Chunk checksum mismatch")
    u["received"][chunk_index]=actual; return {"ack":True,"sha256":actual}
@app.post("/api/v1/upload/complete/{upload_id}")
async def upload_complete(upload_id:str):
    u=uploads.get(upload_id)
    if not u: raise HTTPException(404,"Upload not found")
    if len(u["received"])!=math.ceil(u["size"]/u["chunk"]): raise HTTPException(400,"Missing chunks")
    return {"job_id":await create_job(u["path"]),"status":"queued"}
@app.get("/api/v1/jobs/{job_id}")
async def job(job_id:str):
    j=await jobs.get(job_id)
    if not j: raise HTTPException(404,"Job not found")
    return {"job_id":j.job_id,"status":j.status,"metrics":j.metrics,"error":j.error,"download_url":f"/api/v1/jobs/{job_id}/download" if j.status.value=="done" else None}
@app.get("/api/v1/jobs/{job_id}/download")
async def download(job_id:str):
    j=await jobs.get(job_id)
    if not j or j.status.value!="done": raise HTTPException(404,"Result not ready")
    return FileResponse(j.output,filename=j.output.name)
@app.get("/api/v1/health")
async def health(): return {"status":"ok","ffmpeg":bool(shutil.which(settings.ffmpeg_binary)),"workers":settings.max_workers or 1,"chunk_size":settings.chunk_size}
@app.get("/api/v1/config")
async def config():
    return {"max_file_size":settings.max_file_size,"small_file_threshold":settings.small_file_threshold,"chunk_size":settings.chunk_size,"ssim_threshold":settings.ssim_threshold}
