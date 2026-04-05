"""Helpers for serving the static frontend from FastAPI."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

from app.core.logging import get_logger

logger = get_logger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIR = REPO_ROOT / "frontend"
PAGES_DIR = FRONTEND_DIR / "pages"
ASSETS_DIR = FRONTEND_DIR / "assets"
ENV_JS_PATH = FRONTEND_DIR / "env.js"
FAVICON_PATH = FRONTEND_DIR / "favicon.svg"


def mount_frontend(app: FastAPI) -> None:
    """Serve the static site from the FastAPI app."""
    if not FRONTEND_DIR.exists():
        logger.warning("Frontend directory not found", path=str(FRONTEND_DIR))
        return

    @app.get("/", include_in_schema=False)
    async def root_redirect() -> RedirectResponse:
        return RedirectResponse(url="/pages/index.html", status_code=307)

    @app.get("/pages", include_in_schema=False)
    @app.get("/pages/", include_in_schema=False)
    async def pages_redirect() -> RedirectResponse:
        return RedirectResponse(url="/pages/index.html", status_code=307)

    @app.get("/favicon.svg", include_in_schema=False)
    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon() -> Response:
        if not FAVICON_PATH.exists():
            return Response(status_code=204)
        return FileResponse(FAVICON_PATH, media_type="image/svg+xml")

    @app.get("/env.js", include_in_schema=False)
    async def frontend_env() -> Response:
        if not ENV_JS_PATH.exists():
            logger.warning("Frontend env.js not found", path=str(ENV_JS_PATH))
            return Response(status_code=404)
        return FileResponse(ENV_JS_PATH, media_type="text/javascript; charset=utf-8")

    if PAGES_DIR.exists():
        app.mount("/pages", StaticFiles(directory=PAGES_DIR), name="frontend-pages")
    else:
        logger.warning("Frontend pages directory not found", path=str(PAGES_DIR))

    if ASSETS_DIR.exists():
        app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="frontend-assets")
    else:
        logger.warning("Frontend assets directory not found", path=str(ASSETS_DIR))
