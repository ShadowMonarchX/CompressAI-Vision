from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from app.api.deps import get_job_store
from app.core.exceptions import JobNotFoundError
from app.schemas.models import Job
router=APIRouter(prefix="/jobs",tags=["jobs"])
@router.get("/{job_id}",response_model=Job)
async def job(job_id:str,store=Depends(get_job_store)):
    j=await store.get(job_id)
    if not j: raise JobNotFoundError("Job not found")
    return {"job_id":j.job_id,"status":j.status.value,"metrics":j.metrics,"error":j.error,"download_url":f"/api/v1/jobs/{job_id}/download" if j.status.value=="done" else None}
@router.get("/{job_id}/download",response_class=FileResponse)
async def download(job_id:str,store=Depends(get_job_store)):
    j=await store.get(job_id)
    if not j or j.status.value!="done": raise JobNotFoundError("Result not ready")
    return FileResponse(j.output,filename=j.output.name)
