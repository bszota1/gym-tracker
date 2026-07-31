from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from backend.app.api.routes.analytics import router as analytics_router
from backend.app.api.routes.daily_metrics import router as daily_metrics_router
from backend.app.api.routes.exercises import router as exercises_router
from backend.app.api.routes.workout_sessions import router as workout_sessions_router
from backend.app.api.routes.workout_sets import router as workout_sets_router
from backend.app.core.config import get_settings
from backend.app.core.errors import register_exception_handlers
from backend.app.core.exceptions import NotFoundError
from backend.app.core.logging import get_logger, setup_logging
from backend.app.db.paths import ensure_data_directories
from backend.app.db.session import engine


def create_app() -> FastAPI:
    setup_logging()
    ensure_data_directories()
    settings = get_settings()
    logger = get_logger(__name__)

    app = FastAPI(title="Gym Tracker API", version="0.1.0")
    register_exception_handlers(app)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://127.0.0.1:8501",
            "http://localhost:8501",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/debug/not-found")
    async def debug_not_found() -> None:
        raise NotFoundError("Daily metrics not found")

    @app.get("/readiness")
    async def readiness() -> dict[str, object]:
        checks: dict[str, str] = {
            "database": "down",
            "migrations": "outdated",
            "model_dir": "missing",
        }

        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
                checks["database"] = "ok"

                result = await conn.execute(text("SELECT version_num FROM alembic_version"))
                row = result.first()
                current_rev = row[0] if row else None
        except Exception:
            raise HTTPException(
                status_code=503,
                detail={"status": "not_ready", "checks": checks},
            ) from None

        cfg = Config("alembic.ini")
        script = ScriptDirectory.from_config(cfg)
        head_rev = script.get_current_head()
        if current_rev == head_rev:
            checks["migrations"] = "ok"
        model_dir = Path(settings.model_dir)
        if model_dir.exists() and model_dir.is_dir():
            try:
                probe = model_dir / ".write_probe"
                probe.write_text("ok", encoding="utf-8")
                probe.unlink(missing_ok=True)
                checks["model_dir"] = "ok"
            except OSError:
                checks["model_dir"] = "not_writable"

        ready = all(value == "ok" for value in checks.values())
        if not ready:
            raise HTTPException(
                status_code=503,
                detail={"status": "not_ready", "checks": checks},
            )
        return {"status": "ready", "checks": checks}

    logger.info(
        "Gym Tracker API configured | host=%s port=%s",
        settings.api_host,
        settings.api_port,
    )

    app.include_router(daily_metrics_router)
    app.include_router(exercises_router)
    app.include_router(workout_sessions_router)
    app.include_router(workout_sets_router)
    app.include_router(analytics_router)

    return app


app = create_app()
