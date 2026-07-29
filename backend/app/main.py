from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.config import get_settings
from backend.app.core.errors import register_exception_handlers
from backend.app.core.exceptions import NotFoundError
from backend.app.core.logging import get_logger, setup_logging


def create_app() -> FastAPI:
    setup_logging()
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

    logger.info(
        "Gym Tracker API configured | host=%s port=%s",
        settings.api_host,
        settings.api_port,
    )
    return app


app = create_app()
