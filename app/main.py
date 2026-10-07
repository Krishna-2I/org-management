from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.error_handlers import register_error_handlers
from app.api.middleware import RequestContextMiddleware
from app.api.routes import auth, departments, organizations, stats, tasks, users
from app.core.config import settings
from app.core.logging import setup_logging


def create_app() -> FastAPI:
    setup_logging(settings.log_level)
    app = FastAPI(title=settings.app_name)

    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_error_handlers(app)

    for router in (organizations.router, departments.router, users.router, tasks.router, auth.router, stats.router):
        app.include_router(router, prefix="/api/v1")

    frontend_dir = Path(__file__).resolve().parent.parent / "frontend"

    @app.get("/")
    async def root():
        return FileResponse(frontend_dir / "index.html")

    @app.get("/app.js")
    async def app_js():
        return FileResponse(frontend_dir / "app.js")

    @app.get("/styles.css")
    async def styles_css():
        return FileResponse(frontend_dir / "styles.css")

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app


app = create_app()
