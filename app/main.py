from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles
from app.router.router import router
from app.core.logging import configure_logging
from app.core.exceptions import DomainError
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
@app.exception_handler(DomainError)
async def domain_error_handler(request:Request,exc:DomainError): return JSONResponse(status_code=exc.status_code,content={"error":exc.message,"code":exc.code})
static_dir=Path(__file__).resolve().parent.parent/"static"
if static_dir.is_dir():
    # Keep the canonical mount for CSS/JS/assets and register the entry page
    # explicitly so reloaders and alternate ASGI working directories resolve
    # the UI deterministically.
    app.add_api_route("/static/test.html", lambda: FileResponse(static_dir/"test.html"), methods=["GET"], include_in_schema=False)
    app.mount("/static",StaticFiles(directory=static_dir),name="static")
app.add_api_route("/favicon.ico", lambda: Response(status_code=204), methods=["GET"], include_in_schema=False)
