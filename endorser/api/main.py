"""Main module for initializing and running the Aries Endorser Service.

This module sets up a FastAPI server to host the Endorser service. It configures
logging, sets environment variables, and mounts the main application along with
webhook and endorser routes. The application responds to startup and shutdown events
to register necessary events and manage lifecycle operations.
"""

import logging
import os
import time
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from starlette.middleware import Middleware
from starlette_context import plugins
from starlette_context.middleware import RawContextMiddleware

from api.config import settings
from api.endpoints.routes import (
    connections,
    endorse,
    reports,
    admin,
    allow,
    auth,
    webhooks,
)

# setup loggers
# TODO: set config via env parameters...
logging_file_path = (Path(__file__).parent / "logging.conf").resolve()
logging.config.fileConfig(logging_file_path, disable_existing_loggers=False)

log_level = os.getenv("LOG_LEVEL", "WARNING").upper()
logging.basicConfig(level=log_level)
logging.root.setLevel(level=log_level)

logger = logging.getLogger(__name__)

middleware = [
    Middleware(
        RawContextMiddleware,
        plugins=(plugins.RequestIdPlugin(), plugins.CorrelationIdPlugin()),
    ),
]

os.environ["TZ"] = settings.TIMEZONE
time.tzset()


def endorser_app() -> FastAPI:
    """Create and return a FastAPI application for handling endorser endpoints.

    The application is configured with the specified title, description, debug
    settings, and middleware. It includes a router for managing endorser-related
    endpoints.

    Returns:
        FastAPI: A configured FastAPI application instance.
    """
    app = FastAPI(
        title=settings.TITLE,
        description=settings.DESCRIPTION,
        debug=settings.DEBUG,
        middleware=middleware,
    )
    # mount the token endpoint
    app.include_router(auth.router)

    # mount other endpoints, these will be secured by the above token endpoint
    app.include_router(admin.router, prefix=f"{settings.API_V1_STR}/admin")
    app.include_router(allow.router, prefix=f"{settings.API_V1_STR}/allow")
    app.include_router(connections.router, prefix=f"{settings.API_V1_STR}/connections")
    app.include_router(endorse.router, prefix=f"{settings.API_V1_STR}/endorse")
    app.include_router(reports.router, prefix=f"{settings.API_V1_STR}/reports")

    return app


def webhook_app() -> FastAPI:
    """Create and return a FastAPI application for handling webhooks.

    The application is configured with the specified title, description, debug
    settings, and middleware. It includes a router for managing webhook-related
    endpoints.

    Returns:
        FastAPI: A configured FastAPI application instance.
    """
    app = FastAPI(
        title="WebHooks",
        description="Endpoints for Aca-Py WebHooks",
        debug=settings.DEBUG,
        middleware=None,
    )
    app.include_router(webhooks.router)
    return app


app = FastAPI(
    title=settings.TITLE,
    description=settings.DESCRIPTION,
    debug=settings.DEBUG,
    middleware=None,
)

app.mount("/endorser", endorser_app())
app.mount("/webhook", webhook_app())


@app.on_event("startup")
async def on_endorser_startup():
    """Register any events we need to respond to."""
    logger.warning(">>> Starting up app ...")


@app.on_event("shutdown")
def on_endorser_shutdown():
    """TODO no-op for now."""
    logger.warning(">>> Sutting down app ...")


@app.get("/", tags=["liveness"])
def main():
    """Main function that returns the status and health information.

    Returns:
        dict: A dictionary containing the status and health keys with "ok" values.
    """
    return {"status": "ok", "health": "ok"}


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    uvicorn.run(app, host="0.0.0.0", port=port)
