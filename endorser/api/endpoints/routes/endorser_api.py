"""This module sets up the main API routing for the Aries Endorser Service."""

from fastapi import APIRouter

from api.endpoints.routes import connections, endorse, reports, endorser_admin, allow

endorser_router = APIRouter()
endorser_router.include_router(connections.router, prefix="/connections", tags=[])
endorser_router.include_router(endorse.router, prefix="/endorse", tags=[])
endorser_router.include_router(reports.router, prefix="/reports", tags=[])
endorser_router.include_router(endorser_admin.router, prefix="/admin", tags=[])
endorser_router.include_router(allow.router, prefix="/allow", tags=[])
