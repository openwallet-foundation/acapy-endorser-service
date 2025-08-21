"""This module handles various webhook events for the Endorser Service.

Functions include handling ping, connection requests, connection
status updates, and endorsement transaction requests, responses, and
statuses.

"""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from api.endpoints.models.connections import (
    Connection,
    ConnectionProtocolType,
    webhook_to_connection_object,
)
from api.endpoints.models.endorse import (
    EndorseTransaction,
    webhook_to_txn_object,
)
from api.endpoints.models.witness import WitnessRequest, webhook_to_witness_object
from api.services.connections import (
    set_connection_author_metadata,
    store_connection_request,
    update_connection_status,
)
from api.services.endorse import (
    get_endorser_did,
    store_endorser_request,
    update_endorsement_status,
)
from api.services.witness import (
    store_witness_request,
)

logger = logging.getLogger(__name__)


async def handle_ping_received(db: AsyncSession, payload: dict) -> dict:
    """Handle a received ping message from a connection."""
    logger.info(">>> in handle_ping_received() ...")
    return {}


async def handle_connections_request(db: AsyncSession, payload: dict):
    """Process an incoming connection request and store it in the database."""
    logger.info(">>> in handle_connections_request() ...")
    connection: Connection = webhook_to_connection_object(payload)
    result = await store_connection_request(db, connection)
    return result


async def handle_connections_response(db: AsyncSession, payload: dict):
    """Update connection status based on received connection response."""
    connection: Connection = webhook_to_connection_object(payload)
    result = await update_connection_status(db, connection)
    return result


async def handle_connections_active(db: AsyncSession, payload: dict):
    """Handle a connection becoming active by updating its status."""
    connection: Connection = webhook_to_connection_object(payload)
    result = await update_connection_status(db, connection)
    return result


async def handle_connections_completed(db: AsyncSession, payload: dict):
    """Set endorser role on completed DIDExchange connections."""
    if payload["connection_protocol"] == ConnectionProtocolType.DIDExchange.value:
        connection: Connection = webhook_to_connection_object(payload)
        await set_connection_author_metadata(db, connection)
    return {}


async def handle_endorse_transaction_request_received(db: AsyncSession, payload: dict):
    """Store a received transaction endorsement request."""
    logger.info(">>> in handle_endorse_transaction_request_received() ...")
    endorser_did = await get_endorser_did()
    transaction: EndorseTransaction = webhook_to_txn_object(payload, endorser_did)
    result = await store_endorser_request(db, transaction)
    return result


async def handle_endorse_transaction_transaction_endorsed(
    db: AsyncSession, payload: dict
):
    """Update status for an endorsed transaction."""
    logger.info(">>> in handle_endorse_transaction_transaction_endorsed() ...")
    endorser_did = await get_endorser_did()
    transaction: EndorseTransaction = webhook_to_txn_object(payload, endorser_did)
    result = await update_endorsement_status(db, transaction)
    return result


async def handle_endorse_transaction_transaction_refused(db: AsyncSession, payload: dict):
    """Update status for a refused transaction endorsement."""
    logger.info(">>> in handle_endorse_transaction_transaction_refused() ...")
    endorser_did = await get_endorser_did()
    transaction: EndorseTransaction = webhook_to_txn_object(payload, endorser_did)
    result = await update_endorsement_status(db, transaction)
    return result


async def handle_endorse_transaction_transaction_acked(db: AsyncSession, payload: dict):
    """Update status for an acknowledged transaction endorsement."""
    logger.info(">>> in handle_endorse_transaction_transaction_acked() ...")
    endorser_did = await get_endorser_did()
    transaction: EndorseTransaction = webhook_to_txn_object(payload, endorser_did)
    result = await update_endorsement_status(db, transaction)
    return result


async def handle_log_entry_pending(db: AsyncSession, payload: dict):
    """Update status for a refused log entry."""
    logger.info(">>> in handle_log_entry_pending() ...")
    witness_request: WitnessRequest = webhook_to_witness_object(payload)
    result = await store_witness_request(db, witness_request)
    return result


async def handle_attested_resource_pending(db: AsyncSession, payload: dict):
    """Handle a pending attested resource by storing the witness request."""
    logger.info(">>> in handle_attested_resource_pending() ...")
    witness_request: WitnessRequest = webhook_to_witness_object(payload)
    result = await store_witness_request(db, witness_request)
    return result
