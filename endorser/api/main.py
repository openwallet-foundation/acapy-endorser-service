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

from api.core.config import settings
from api.endorser_main import get_endorserapp
from api.endpoints.routes.webhooks import get_webhookapp

# setup loggers
# TODO: set config via env parameters...
logging_file_path = (Path(__file__).parent / "logging.conf").resolve()
logging.config.fileConfig(logging_file_path, disable_existing_loggers=False)

log_level = os.getenv("LOG_LEVEL", "WARNING")
log_level = log_level.upper()
logging.basicConfig(level=log_level)
logging.root.setLevel(level=log_level)

logger = logging.getLogger(__name__)

os.environ["TZ"] = settings.TIMEZONE
time.tzset()


def get_application() -> FastAPI:
    """Create and return a FastAPI application instance."""

    application = FastAPI(
        title=settings.TITLE,
        description=settings.DESCRIPTION,
        debug=settings.DEBUG,
        middleware=None,
    )
    return application


app = get_application()
webhook_app = get_webhookapp()
app.mount("/webhook", webhook_app)

endorser_app = get_endorserapp()
app.mount("/endorser", endorser_app)


@app.on_event("startup")
async def on_endorser_startup():
    """Register any events we need to respond to."""
    logger.warning(">>> Starting up app ...")


@app.on_event("shutdown")
def on_endorser_shutdown():
    """TODO no-op for now."""
    logger.warning(">>> Sutting down app ...")
    pass


@app.get("/", tags=["liveness"])
def main():
    """Main function that returns the status and health information.

    Returns:
        dict: A dictionary containing the status and health keys with "ok" values.
    """
    return {"status": "ok", "health": "ok"}


if __name__ == "__main__":
    print("main.")
    uvicorn.run(app, host="0.0.0.0", port=5300)
