"""FastAPI web console for LongTextAgent."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, Response

from writing_agent.config import Settings, get_settings
from writing_agent.web.routes import collections, documents, evaluation, files, health, jobs
from writing_agent.web.routes import templates as template_routes

WEB_DIR = Path(__file__).parent
STATIC_DIR = WEB_DIR / "static"
TEMPLATE_DIR = STATIC_DIR / "templates"


def _read_template(name: str) -> str:
    return (TEMPLATE_DIR / name).read_text(encoding="utf-8")


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create the FastAPI web console app."""

    resolved_settings = settings or get_settings()
    app = FastAPI(title="LongTextAgent Web Console", version="0.1.0")
    app.state.settings = resolved_settings

    @app.get("/", response_class=HTMLResponse)
    async def index() -> str:
        return _read_template("index.html")

    @app.get("/jobs/{job_id}", response_class=HTMLResponse)
    async def job_detail(job_id: str) -> str:
        return _read_template("job_detail.html").replace("__JOB_ID__", job_id)

    @app.get("/collections", response_class=HTMLResponse)
    async def collections_page() -> str:
        return _read_template("collections.html")

    @app.get("/documents", response_class=HTMLResponse)
    async def documents_page() -> str:
        return _read_template("documents.html")

    @app.get("/settings", response_class=HTMLResponse)
    async def settings_page() -> str:
        return _read_template("settings.html")

    @app.get("/static/{asset_name}")
    async def static_asset(asset_name: str) -> Response:
        path = STATIC_DIR / asset_name
        if not path.exists() or not path.is_file():
            return Response(status_code=404)
        media_type = "text/css" if path.suffix == ".css" else "application/javascript"
        return Response(path.read_text(encoding="utf-8"), media_type=media_type)

    api_prefix = "/api"
    app.include_router(health.router, prefix=api_prefix)
    app.include_router(jobs.router, prefix=api_prefix)
    app.include_router(files.router, prefix=api_prefix)
    app.include_router(collections.router, prefix=api_prefix)
    app.include_router(documents.router, prefix=api_prefix)
    app.include_router(evaluation.router, prefix=api_prefix)
    app.include_router(template_routes.router, prefix=api_prefix)

    @app.get("/api/config")
    async def config_compat() -> dict[str, str | None]:
        return resolved_settings.safe_summary()

    return app


app = create_app()
