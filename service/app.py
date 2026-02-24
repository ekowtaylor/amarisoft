"""FastAPI application factory for the Amarisoft REST API service.

Creates and configures the FastAPI application with all routers,
middleware, and lifecycle events.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from client.websocket.exceptions import AmariError

from . import __version__
from .config import Settings, get_settings
from .exceptions import APIError, InternalServerError, map_amarisoft_exception
from .manager import CallboxManager, clear_manager, set_manager
from .routers import enb_router, ims_router, mme_router, system_router, ue_router

if TYPE_CHECKING:
    from .config import Settings

logger = logging.getLogger(__name__)


def _configure_logging(settings: Settings) -> None:
    """Configure logging based on settings.

    Args:
        settings: Application settings.
    """
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Set log levels for specific loggers
    logging.getLogger("amarisoft").setLevel(log_level)
    logging.getLogger("service").setLevel(log_level)

    # Reduce noise from uvicorn access logs at INFO level
    if log_level > logging.DEBUG:
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def _create_lifespan(settings: Settings):
    """Create the lifespan context manager for the app.

    Args:
        settings: Application settings.

    Returns:
        Async context manager for app lifespan.
    """

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
        """Manage application startup and shutdown.

        Creates the CallboxManager on startup and closes connections
        on shutdown.
        """
        logger.info("Starting Amarisoft REST API service v%s", __version__)
        logger.info("Callbox host: %s", settings.callbox_host)
        logger.info(
            "Service ports - eNB: %d, MME: %d, IMS: %d, UE: %d",
            settings.enb_port,
            settings.mme_port,
            settings.ims_port,
            settings.ue_port,
        )

        # Create and register the manager
        manager = CallboxManager(settings)
        set_manager(manager)

        logger.info("REST API listening on %s:%d", settings.host, settings.port)

        yield

        # Cleanup on shutdown
        logger.info("Shutting down Amarisoft REST API service")
        clear_manager()
        logger.info("All connections closed")

    return lifespan


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        settings: Optional settings instance. If not provided,
            settings are loaded from environment variables.

    Returns:
        Configured FastAPI application instance.
    """
    if settings is None:
        settings = get_settings()

    # Configure logging
    _configure_logging(settings)

    # Create the FastAPI app
    app = FastAPI(
        title="Amarisoft REST API",
        description=(
            "HTTP REST interface for Amarisoft Callbox WebSocket API. "
            "Provides access to eNB/gNB, MME/AMF, IMS, and UE Simulator services."
        ),
        version=__version__,
        lifespan=_create_lifespan(settings),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Store settings in app state for access in routes
    app.state.settings = settings

    # Add CORS middleware if enabled
    if settings.enable_cors:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(settings.cors_origins),
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Register exception handlers
    _register_exception_handlers(app)

    # Register routers
    app.include_router(system_router)
    app.include_router(enb_router)
    app.include_router(mme_router)
    app.include_router(ims_router)
    app.include_router(ue_router)

    # Add request logging middleware
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        """Log incoming requests."""
        logger.debug(
            "%s %s",
            request.method,
            request.url.path,
        )
        response = await call_next(request)
        logger.debug(
            "%s %s -> %d",
            request.method,
            request.url.path,
            response.status_code,
        )
        return response

    logger.info("FastAPI application created")
    return app


def _register_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers.

    Args:
        app: FastAPI application instance.
    """

    @app.exception_handler(APIError)
    async def api_error_handler(_request: Request, exc: APIError) -> JSONResponse:
        """Handle APIError exceptions."""
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.detail,
        )

    @app.exception_handler(AmariError)
    async def amari_error_handler(_request: Request, exc: AmariError) -> JSONResponse:
        """Handle Amarisoft exceptions by mapping to HTTP errors."""
        api_error = map_amarisoft_exception(exc)
        return JSONResponse(
            status_code=api_error.status_code,
            content=api_error.detail,
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(_request: Request, exc: ValueError) -> JSONResponse:
        """Handle ValueError as bad request."""
        return JSONResponse(
            status_code=400,
            content={
                "error": "Bad request",
                "detail": str(exc),
                "error_code": "BAD_REQUEST",
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(
        _request: Request, exc: Exception
    ) -> JSONResponse:
        """Handle unexpected exceptions."""
        logger.exception("Unexpected error: %s", exc)
        error = InternalServerError(detail=str(exc))
        return JSONResponse(
            status_code=error.status_code,
            content=error.detail,
        )
