"""Module for handling endorsement transactions in the Aries Endorser Service.

This module includes enumerations for endorser role types, transaction
states and types, and models for representing and converting
endorsement transactions between various forms, such as payloads,
model objects, and database entities. It provides utility functions to
convert transactions from webhooks or database objects into the
endorser service's model format.

"""

from enum import Enum
import json
import logging
from uuid import UUID
from pydantic import BaseModel

from api.db.models.endorse_request import EndorseRequest


logger = logging.getLogger(__name__)


class EndorserRoleType(str, Enum):
    """Define roles for an Endorser in the transaction process."""

    Author = "TRANSACTION_AUTHOR"
    Endorser = "TRANSACTION_ENDORSER"


class EndorseTransactionState(str, Enum):
    """Enumerate possible states of an endorsement transaction."""

    transaction_created = "transaction_created"
    request_sent = "request_sent"
    request_received = "request_received"
    transaction_endorsed = "transaction_endorsed"
    transaction_refused = "transaction_refused"
    transaction_resent = "transaction_resent"
    transaction_resent_received = "transaction_resent_received"
    transaction_cancelled = "transaction_cancelled"
    transaction_acked = "transaction_acked"


class EndorseTransactionType(str, Enum):
    """Enumerate types of transactions for endorsement."""

    did = "1"
    attrib = "100"
    schema = "101"
    cred_def = "102"
    revoc_registry = "113"
    revoc_entry = "114"


class EndorseTransaction(BaseModel):
    """Represent an endorsement transaction."""

    author_goal_code: str | None = None
    connection_id: UUID
    transaction_id: UUID
    tags: list[str]
    created_at: str | None = None
    state: str
    transaction_request: dict | None = None
    endorser_did: str
    author_did: str | None = None
    transaction: dict | None = None
    transaction_type: str | None = None
    transaction_response: dict | None = None


class EndorseTransactionList(BaseModel):
    """Contain a paginated list of endorsement transactions."""

    page_size: int
    page_num: int
    count: int
    total_count: int
    transactions: list[EndorseTransaction]


def webhook_to_txn_object(payload: dict, endorser_did: str) -> EndorseTransaction:
    """Convert from a webhook payload to an endorser transaction."""
    logger.debug(f">>> from payload: {payload}")
    if (
        "json" in payload["messages_attach"][0]["data"]
        and payload["messages_attach"][0]["data"]["json"]
    ):
        # deal with str or dict types
        payload_json = payload["messages_attach"][0]["data"]["json"]
        if isinstance(payload_json, dict):
            transaction_request = payload_json
        else:
            transaction_request = json.loads(payload_json)
    else:
        transaction_request = {}
    if 0 < len(payload["signature_response"]):
        transaction_response = (
            json.loads(payload["signature_response"][0]["signature"][endorser_did])
            if payload["signature_response"][0]["signature"][endorser_did]
            else None
        )
    else:
        transaction_response = {}
    transaction: EndorseTransaction = EndorseTransaction(
        author_goal_code=payload.get("signature_request", [])[0].get(
            "author_goal_code"
        ),
        connection_id=UUID(payload.get("connection_id")),
        transaction_id=UUID(payload.get("transaction_id")),
        tags=[],
        state=str(payload.get("state")),
        transaction_request=transaction_request,
        endorser_did=endorser_did,
        author_did=(
            transaction_request["identifier"]
            if transaction_request and "identifier" in transaction_request
            else None
        ),
        transaction=(
            transaction_request["operation"]
            if transaction_request and "operation" in transaction_request
            else None
        ),
        transaction_type=(
            transaction_request["operation"]["type"]
            if transaction_request and "operation" in transaction_request
            else None
        ),
        transaction_response=transaction_response,
    )
    logger.debug(f">>> to transaction: {transaction}")
    return transaction


def txn_to_db_object(txn: EndorseTransaction) -> EndorseRequest:
    """Convert from model object to database model object."""
    logger.debug(f">>> from transaction: {txn}")
    txn_request: EndorseRequest = EndorseRequest(
        author_goal_code=txn.author_goal_code,
        transaction_id=txn.transaction_id,
        connection_id=txn.connection_id,
        tags=txn.tags,
        endorser_did=txn.endorser_did,
        author_did=txn.author_did,
        transaction_type=txn.transaction_type,
        state=txn.state,
        ledger_txn=json.dumps(txn.transaction),
        ledger_txn_request=json.dumps(txn.transaction_request),
    )
    logger.debug(f">>> to request: {txn_request}")
    return txn_request


def db_to_txn_object(
    txn_request: EndorseRequest, acapy_txn: dict | None = None
) -> EndorseTransaction:
    """Convert from database and acapy objects to model object."""
    if acapy_txn:
        transaction_request = json.loads(
            acapy_txn["messages_attach"][0]["data"]["json"]
        )
        transaction_request.get("operation")
        if 0 < len(acapy_txn["signature_response"]):
            transaction_response = json.loads(
                acapy_txn["signature_response"][0]["signature"][
                    txn_request.endorser_did
                ]
            )
        else:
            transaction_response = {}
    else:
        transaction_response = {}
    txn: EndorseTransaction = EndorseTransaction(
        author_goal_code=(
            str(txn_request.author_goal_code) if txn_request.author_goal_code else None
        ),
        connection_id=txn_request.connection_id,
        transaction_id=txn_request.transaction_id,
        tags=txn_request.tags,
        state=acapy_txn.get("state") if acapy_txn else txn_request.state,
        endorser_did=txn_request.endorser_did,
        author_did=txn_request.author_did,
        created_at=str(txn_request.created_at),
        transaction=json.loads(txn_request.ledger_txn),
        transaction_request=(
            json.loads(txn_request.ledger_txn_request)
            if txn_request.ledger_txn_request
            else None
        ),
        transaction_type=txn_request.transaction_type,
        transaction_response=transaction_response,
    )
    return txn
