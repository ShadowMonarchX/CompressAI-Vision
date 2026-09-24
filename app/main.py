from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import ORJSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from app.api.v1 import router as v1_router
from app.core.exceptions import DomainError
app=FastAPI(title="CompressAI Vision",version="1.0.0",default_response_class=ORJSONResponse)
app.include_router(v1_router)
@app.exception_handler(DomainError)
async def domain_error_handler(request:Request,exc:DomainError): return ORJSONResponse(status_code=exc.status_code,content={"error":exc.message,"code":exc.code})
static_dir=Path(__file__).resolve().parent.parent/"static"
if static_dir.is_dir(): app.mount("/static",StaticFiles(directory=static_dir),name="static")
