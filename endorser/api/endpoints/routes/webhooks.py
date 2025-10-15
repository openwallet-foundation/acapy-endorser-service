"""Module for handling Aca-Py WebHook endpoints in the Endorser Agent.

This module defines a FastAPI application and router to process
incoming webhook events from an Aries Cloudagent (Aca-Py). It provides
endpoints for validating and processing webhook data based on various
topics and state changes, and includes dependency injection for
authentication and database session management. Handlers for different
webhook topics and states are dynamically invoked from the
api_services module, and auto-steppers may be used to progress to
subsequent states.

"""

import logging
import traceback
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, Security
from fastapi.security.api_key import APIKey, APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import HTTP_403_FORBIDDEN

import api.services as api_services
from api.config import settings
from api.endpoints.dependencies.db import get_db
from api.endpoints.models.connections import Connection
from api.endpoints.models.endorse import EndorseTransaction
# from api.endpoints.models.witness import WitnessRequest

logger = logging.getLogger(__name__)

router = APIRouter(tags=["webhooks"])

api_key_header = APIKeyHeader(
    name=settings.ACAPY_WEBHOOK_URL_API_KEY_NAME, auto_error=False
)


class WebhookTopicType(str, Enum):
    """Enumeration of various webhook topic types for handling different events."""

    ping = "ping"
    connections = "connections"
    oob_invitation = "oob-invitation"
    connection_reuse = "connection-reuse"
    connection_reuse_accepted = "connection-reuse-accepted"
    basicmessages = "basicmessages"
    issue_credential = "issue-credential"
    issue_credential_v2_0 = "issue-credential-v2-0"
    issue_credential_v2_0_indy = "issue-credential-v2-0-indy"
    issue_credential_v2_0_ld_proof = "issue-credential-v2-0-ld-proof"
    issuer_cred_rev = "issuer-cred-rev"
    present_proof = "present-proof"
    present_proof_v2_0 = "present-proof-v2-0"
    endorse_transaction = "endorse_transaction"
    revocation_registry = "revocation-registry"
    revocation_notification = "revocation-notification"
    problem_report = "problem-report"
    log_entry = "log-entry"
    attested_resource = "attested-resource"


async def get_api_key(
    api_key_header: str = Security(api_key_header),
):
    """Get API key from header and validate against settings."""
    if api_key_header == settings.ACAPY_WEBHOOK_URL_API_KEY:
        return api_key_header
    else:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN, detail="Could not validate credentials"
        )


@router.post("/topic/{topic}/", response_model=dict | Connection | EndorseTransaction)
async def process_webhook(
    topic: WebhookTopicType,
    payload: dict,
    api_key: APIKey = Depends(get_api_key),
    db: AsyncSession = Depends(get_db),
):
    """Called by aca-py agent."""
    state = payload.get("state")
    if state:
        logger.info(f">>> Called webhook for endorser: {topic.name} / {state}")
    else:
        logger.info(f">>> Called webhook for endorser: {topic.name}")
    logger.debug(f">>> payload: {payload}")

    # call the handler to process the hook, if present
    result = {}
    try:
        handler = f"handle_{topic.name}_{state}" if state else f"handle_{topic.name}"
        handler = handler.replace("-", "_")
        if hasattr(api_services, handler):
            result = await getattr(api_services, handler)(db, payload)
            logger.debug(f">>> {handler} returns = {result}")
        else:
            logger.warn(f">>> no webhook handler available for: {handler}")
    except Exception as e:
        logger.error(">>> handler returned error:" + str(e))
        traceback.print_exc()
        return result

    try:
        # call the "auto-stepper" if we have one, to move to the next state
        stepper = (
            f"auto_step_{topic.name}_{state}" if state else f"auto_step_{topic.name}"
        )
        stepper = stepper.replace("-", "_")
        if hasattr(api_services, stepper):
            _stepper_result = await getattr(api_services, stepper)(db, payload, result)
            logger.debug(f">>> {stepper} returns = {_stepper_result}")
        else:
            logger.warn(f">>> no webhook stepper available for: {stepper}")
    except Exception as e:
        logger.error(">>> auto-stepper returned error:" + str(e))
        traceback.print_exc()

    return result if isinstance(result, dict) else result.model_dump()
