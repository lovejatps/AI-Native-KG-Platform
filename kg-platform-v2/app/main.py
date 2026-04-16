from fastapi import FastAPI
from app.api.routes import router  # type: ignore

from fastapi.staticfiles import StaticFiles
import os

app = FastAPI(title="KG Platform V2")
# Log configuration details at startup
from app.core.logger import get_logger
from app.core.config import get_settings

_logger = get_logger(__name__)
_logger.info(f"LLM_MAX_OUTPUT_TOKENS set to {get_settings().LLM_MAX_OUTPUT_TOKENS}")

# Mount static frontend files

frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "frontend"))
app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

app.include_router(router)


from fastapi.responses import FileResponse


@app.get("/")
def root():
    # Serve the UI entry page (index.html)
    index_path = os.path.join(frontend_dir, "index.html")
    return FileResponse(index_path)
