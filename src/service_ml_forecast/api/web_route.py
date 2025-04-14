from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from service_ml_forecast.config import ENV

# spa router takes care of the prefix
# don't include in the docs as its not an API endpoint
router = APIRouter(include_in_schema=False)

# Get the web dist directory path from environment
web_dist_dir = Path(ENV.ML_WEB_DIST_DIR)

if not web_dist_dir.exists():
    raise RuntimeError(f"Web dist directory not found at {web_dist_dir}")

# Mount static files
router.mount("/static", StaticFiles(directory=str(web_dist_dir)), name="static")


@router.get("/", summary="Serve the index.html file from the web dist directory.")
async def serve_index() -> FileResponse:
    """Serve the index.html file from the web dist directory."""

    index_path = web_dist_dir / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="index.html not found")
    return FileResponse(index_path)


@router.get("/{path:path}", summary="Serve static files or return index.html for SPA routing.")
async def serve_spa(path: str) -> FileResponse:
    """Serve static files or return index.html for SPA routing."""

    requested_path = web_dist_dir / path

    # If the exact file exists, serve it (e.g. css, images, etc.)
    if requested_path.is_file():
        return FileResponse(requested_path)

    # Return index.html for client-side routing
    index_path = web_dist_dir / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="index.html not found")
    return FileResponse(index_path)
