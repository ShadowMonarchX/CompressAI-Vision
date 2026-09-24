from pathlib import Path
import logging, uuid
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles
from app.router.router import router
from app.core.logging import configure_logging
from app.core.exceptions import AppError
configure_logging()
app=FastAPI(
    title="CompressAI Vision",
    version="1.0.0",
    openapi_tags=[
        {"name": "health", "description": "Service health and configuration."},
        {"name": "compress", "description": "Compression job submission."},
        {"name": "upload", "description": "Upload management."},
        {"name": "jobs", "description": "Compression job status."},
        {"name": "compare", "description": "AI-assisted versus fixed-baseline compression."},
        {"name": "v2", "description": "Reserved for the v2 API surface."},
    ],
)
app.include_router(router)
logger = logging.getLogger(__name__)
@app.middleware("http")
async def request_id(request, call_next):
    request.state.request_id = request.headers.get("X-Request-ID", uuid.uuid4().hex)
    response = await call_next(request); response.headers["X-Request-ID"] = request.state.request_id; return response
def error_response(request, status, code, message, detail=None):
    return JSONResponse(status_code=status, content={"error_code":code,"message":message,"detail":detail,"request_id":request.state.request_id})
@app.exception_handler(AppError)
async def app_error_handler(request:Request, exc:AppError):
    logger.log(logging.WARNING if exc.status_code < 500 else logging.ERROR, "request_id=%s error=%s context=%s", request.state.request_id, exc.error_code, exc.context, exc_info=exc.status_code >= 500)
    return error_response(request, exc.status_code, exc.error_code, exc.message, exc.context or None)
@app.exception_handler(RequestValidationError)
async def validation_handler(request, exc):
    return error_response(request, 400, "validation_error", "Request validation failed", {"fields": exc.errors()})
@app.exception_handler(Exception)
async def unhandled_handler(request, exc):
    logger.error("request_id=%s unhandled exception", request.state.request_id, exc_info=exc)
    return error_response(request, 500, "internal_error", "Internal server error")
static_dir=Path(__file__).resolve().parent.parent/"static"
if static_dir.is_dir():
    # Keep the canonical mount for CSS/JS/assets and register the entry page
    # explicitly so reloaders and alternate ASGI working directories resolve
    # the UI deterministically.
    app.add_api_route("/static/test.html", lambda: FileResponse(static_dir/"test.html"), methods=["GET"], include_in_schema=False)
    app.mount("/static",StaticFiles(directory=static_dir),name="static")
app.add_api_route("/favicon.ico", lambda: Response(status_code=204), methods=["GET"], include_in_schema=False)
