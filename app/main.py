from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles
from app.api.v1 import router as v1_router
from app.core.exceptions import DomainError
app=FastAPI(title="CompressAI Vision",version="1.0.0")
app.include_router(v1_router)
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
