"""FastAPI application entry point for Candidate Screening Agent."""

import sys
import asyncio

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app import __version__
from app.core.config import get_settings
from app.core.logging import setup_logging, get_logger
from app.api.routes import health, candidates, runs, events
from app.database.session import init_db

logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    settings = get_settings()
    setup_logging(settings.LOG_LEVEL)
    logger.info("Starting Candidate Screening Agent backend (version %s)", __version__)
    logger.info("Environment: %s | Dry run: %s", settings.ENVIRONMENT, settings.DRY_RUN)

    def _prepare_databases() -> None:
        try:
            init_db("all")
            logger.info("Databases initialized")
        except Exception:
            logger.exception("Database initialization failed")

    asyncio.get_running_loop().run_in_executor(None, _prepare_databases)
    yield
    logger.info("Shutting down Candidate Screening Agent backend")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Candidate Screening Agent API",
        description="Local screening agent backend for Instahyre + GitHub Go/Golang verification",
        version=__version__,
        lifespan=lifespan,
    )

    settings = get_settings()
    origins = [item.strip() for item in settings.CORS_ORIGINS.split(",") if item.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_origin_regex=r"https://.*\.vercel\.app",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routes
    app.include_router(health.router)
    app.include_router(candidates.router)
    app.include_router(runs.router)
    app.include_router(events.router)

    return app


app = create_app()
