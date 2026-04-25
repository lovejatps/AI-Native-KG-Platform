from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from app.api.routes import router  # type: ignore
from app.api.semantic_dict import router as semantic_router  # type: ignore
from app.auth.router import router as auth_router  # type: ignore

from fastapi.staticfiles import StaticFiles
import os

app = FastAPI(title="KG Platform V2")

# Initialise the placeholder business DB when the app starts (idempotent)
from app.core.init_business_db import init_business_db


# Import logger and middleware before usage
from app.core.logger import get_logger
from app.auth.middleware import JWTAuthMiddleware

_logger = get_logger(__name__)


# Centralized error handling – return a consistent JSON structure
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail, "error": exc.detail})


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    # Log the unexpected error
    _logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(status_code=500, content={"error": "Internal server error"})


# Add JWT auth middleware (now JWTAuthMiddleware is defined)
app.add_middleware(JWTAuthMiddleware)

# Log configuration details at startup
from app.core.config import get_settings

_logger.info(f"LLM_MAX_OUTPUT_TOKENS set to {get_settings().LLM_MAX_OUTPUT_TOKENS}")

# Initialise business DB on FastAPI startup – idempotent
@app.on_event("startup")
def _startup_init_db():
    init_business_db()
    _logger.info("Business SQLite DB initialised (or already present)")

# Mount static frontend files

frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "frontend"))
app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

app.include_router(router)
app.include_router(semantic_router)
app.include_router(auth_router)


from fastapi.responses import FileResponse


@app.get("/")
def root():
    # Serve the UI entry page (index.html)
    index_path = os.path.join(frontend_dir, "index.html")
    return FileResponse(index_path)
