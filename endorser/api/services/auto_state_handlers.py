"""Automated processing for endorsement transactions and connections in Aries.

This module provides functionality to automatically manage endorsement
transactions and connections within an Aries-based endorser service. It allows
for the automatic acceptance, endorsement, or rejection of transactions based
on configurable criteria, enhancing the efficiency of interactions in a secure
digital identity environment.

Functions include utilities for determining auto-endorsement capabilities,
managing transaction states, and handling connection requests with async
database operations.
"""

import logging
import traceback
from typing import Any, cast

from attr import dataclass
from sqlalchemy import or_, select
from sqlalchemy.engine.row import Row
from sqlalchemy.ext.asyncio import AsyncSession

import api.acapy_utils as au
from api.db.models.allow import (
    AllowedCredentialDefinition,
    AllowedSchema,
    AllowedLogEntry,
)
from api.endpoints.models.allow import (
    AllowedPublicDid,
)
from api.endpoints.models.connections import (
    AuthorStatusType,
    Connection,
    EndorseStatusType,
    webhook_to_connection_object,
)
from api.endpoints.models.endorse import (
    EndorseTransaction,
    EndorseTransactionType,
    webhook_to_txn_object,
)
from api.endpoints.models.witness import WitnessRequest
from api.services.configurations import (
    get_bool_config,
    get_config,
)
from api.services.connections import (
    accept_connection_request,
    get_connection_object,
)
from api.services.endorse import (
    endorse_transaction,
    get_endorser_did,
    reject_transaction,
)
from api.services.witness import (
    witness_request,
    reject_request,
)

logger = logging.getLogger(__name__)


def is_auto_endorse_connection(connection: Connection) -> bool:
    """Check if a connection is set up for auto-endorse."""
    return (
        connection.author_status.name is AuthorStatusType.active.name
        and connection.endorse_status.name is EndorseStatusType.auto_endorse.name
    )


def is_auto_reject_connection(connection: Connection) -> bool:
    """Determine if a connection is set for auto-rejection.

    Args:
        connection Connection: A Connection object to evaluate
    Returns:
        bool: True if connection should be auto-rejected, False otherwise
    """
    return (
        connection.author_status.name is AuthorStatusType.active.name
        and connection.endorse_status.name is EndorseStatusType.auto_reject.name
    )


async def is_auto_endorse_txn(
    db: AsyncSession, transaction: EndorseTransaction, connection: Connection
):
    """Determine if a transaction should be auto-endorsed.

    Args:
        db (AsyncSession): Database session for querying configurations.
        transaction (EndorseTransaction): Transaction to be checked.
        connection (Connection): Connection associated with the transaction.

    Returns:
        bool: True if the transaction should be auto-endorsed, otherwise False.
    """
    auto_req = await get_bool_config(db, "ENDORSER_AUTO_ENDORSE_REQUESTS")
    auto_req_type = await get_config(db, "ENDORSER_AUTO_ENDORSE_TXN_TYPES")
    if auto_req or is_auto_endorse_connection(connection):
        if auto_req_type is None or len(auto_req_type) == 0:
            return True
        txn_type = transaction.transaction_type
        auto_req_types = auto_req_type.split(",")
        return txn_type in auto_req_types

    return False


async def auto_step_ping_received(
    db: AsyncSession, payload: dict, handler_result: dict
) -> dict:
    """Process a received ping and return an empty dictionary."""
    return {}


async def auto_step_connections_request(
    db: AsyncSession, payload: dict, handler_result: dict
) -> dict | Connection:
    """Handle connection requests, auto-accepting if configured."""
    connection: Connection = webhook_to_connection_object(payload)
    if await get_bool_config(db, "ENDORSER_AUTO_ACCEPT_CONNECTIONS"):
        await accept_connection_request(db, connection)
    return {}


async def auto_step_connections_response(
    db: AsyncSession, payload: dict, handler_result: dict
) -> dict:
    """Handle response for auto step connections - no operation currently."""
    return {}


async def auto_step_connections_active(
    db: AsyncSession, payload: dict, handler_result: dict
) -> dict:
    """Handle active auto step connections - no operation currently."""
    return {}


async def auto_step_connections_completed(
    db: AsyncSession, payload: dict, handler_result: dict
) -> dict:
    """Handle completed auto step connections - no operation currently."""
    return {}


@dataclass
class CreddefCriteria:
    """Criteria for identifying credential definitions."""

    DID: str
    Schema_Issuer_DID: str
    Schema_Name: str
    Schema_Version: str
    Tag: str


@dataclass
class SchemaCriteria:
    """Criteria for identifying schemas."""

    DID: str
    Name: str
    Version: str


@dataclass
class LogEntryCriteria:
    """Criteria for identifying log entries."""

    scid: str
    domain: str
    namespace: str
    identifier: str


def eq_or_wild(indb, clause: str | Any):
    """Evaluate equality with wildcard support."""
    if isinstance(clause, str):
        return or_(indb == clause, indb == "*")
    else:
        return indb == clause


async def check_auto_endorse(
    db: AsyncSession,
    table: type,
    filters: list[tuple[Any, Any]],
) -> bool:
    """Check if a transaction can be auto-endorsed based on configured filters."""
    wild_filters = [eq_or_wild(x, y) for x, y in filters]
    q = select(table).filter(*wild_filters)
    result = await db.execute(q)
    result_rec: Row | None = result.one_or_none()
    logger.debug(f"got the following record {result_rec} with query {q}")
    if result_rec:
        return True
    else:
        return False


async def allowed_publish_did(db: AsyncSession, did: str) -> bool:
    """Check if publishing a DID is allowed."""
    return await check_auto_endorse(
        db, AllowedPublicDid, [(AllowedPublicDid.registered_did, did)]
    )


async def allowed_log_entry(db: AsyncSession, log_entry: LogEntryCriteria) -> bool:
    """Check if creating a log entry is allowed."""
    return await check_auto_endorse(
        db,
        AllowedLogEntry,
        [
            (AllowedLogEntry.scid, log_entry.scid),
            (AllowedLogEntry.domain, log_entry.domain),
            (AllowedLogEntry.namespace, log_entry.namespace),
            (AllowedLogEntry.identifier, log_entry.identifier),
        ],
    )


async def allowed_schema(db: AsyncSession, schema_trans: SchemaCriteria) -> bool:
    """Check if creating a schema is allowed."""
    return await check_auto_endorse(
        db,
        AllowedSchema,
        [
            (AllowedSchema.author_did, schema_trans.DID),
            (AllowedSchema.schema_name, schema_trans.Name),
            (AllowedSchema.version, schema_trans.Version),
        ],
    )


async def allowed_creddef(db: AsyncSession, creddef_trans: CreddefCriteria) -> bool:
    """Check if creating a credential definition is allowed."""
    return await check_auto_endorse(
        db,
        AllowedCredentialDefinition,
        [
            (AllowedCredentialDefinition.creddef_author_did, creddef_trans.DID),
            (
                AllowedCredentialDefinition.schema_issuer_did,
                creddef_trans.Schema_Issuer_DID,
            ),
            (AllowedCredentialDefinition.schema_name, creddef_trans.Schema_Name),
            (AllowedCredentialDefinition.version, creddef_trans.Schema_Version),
            (AllowedCredentialDefinition.tag, creddef_trans.Tag),
        ],
    )


async def is_endorsable_transaction(db: AsyncSession, trans: EndorseTransaction) -> bool:
    """Determine if a transaction can be endorsed based on its type and attributes."""
    logger.debug(">>> from is_endorsable_transaction: entered")

    # Publishing/registering a public did on the ledger
    if (
        trans.author_goal_code == "aries.transaction.register_public_did"
        or trans.transaction_type == EndorseTransactionType.did
        or trans.transaction_type == EndorseTransactionType.attrib
    ):
        return await allowed_publish_did(
            db,
            # The location of the DID depends on if the author already
            # has a public DID or not
            (
                str(trans.transaction_request.get("did"))
                if trans.author_goal_code == "aries.transaction.register_public_did"
                and trans.transaction_request.get("did")
                else str(trans.transaction.get("dest"))
            ),
        )
    else:
        # The author must already have a DID and a transaction in
        # order to do any of this
        if (not trans.author_did) or (not trans.transaction):
            return False

        match trans.transaction_type:
            case EndorseTransactionType.revoc_registry:
                logger.debug(
                    f">>> is_endorsable_transaction: {trans} was a revocation registry"
                )
                # ex "3w88pmVPfeVaz8bMukH2uR:3:CL:81268:default"
                credDefId: list[str] = trans.transaction["credDefId"].split(":")
                cred_auth_did = credDefId[0]
                sequence_num = int(credDefId[3])
                tag = credDefId[4]

                logger.debug(
                    f">>> from is_endorsable_transaction: {trans} awaiting schema"
                )
                response = cast(dict, await au.acapy_GET("schemas/" + str(sequence_num)))
                schema_id: list[str] = response["schema"]["id"].split(":")

                return await check_auto_endorse(
                    db,
                    AllowedCredentialDefinition,
                    [
                        (AllowedCredentialDefinition.creddef_author_did, cred_auth_did),
                        (AllowedCredentialDefinition.schema_issuer_did, schema_id[0]),
                        (AllowedCredentialDefinition.schema_name, schema_id[2]),
                        (AllowedCredentialDefinition.version, schema_id[3]),
                        (AllowedCredentialDefinition.tag, tag),
                        (AllowedCredentialDefinition.rev_reg_def, True),
                    ],
                )
            case EndorseTransactionType.revoc_entry:
                logger.debug(
                    f">>> from is_endorsable_transaction: {trans} was a revocation entry"
                )
                # ex "3w88pmVPfeVaz8bMukH2uR:3:CL:81268:default"
                revocRegDefId: list[str] = trans.transaction["revocRegDefId"].split(":")

                cred_auth_did = revocRegDefId[0]
                sequence_num = int(revocRegDefId[5])
                tag = revocRegDefId[6]

                logger.debug(
                    f">>> from is_endorsable_transaction: {trans} awaiting schema"
                )
                response = cast(dict, await au.acapy_GET("schemas/" + str(sequence_num)))
                schema_id: list[str] = response["schema"]["id"].split(":")
                logger.debug(
                    f">>> from is_endorsable_transaction: {trans} was a revocation entry"
                )
                # raise Exception("revoc_entry not implemented", trans)
                return await check_auto_endorse(
                    db,
                    AllowedCredentialDefinition,
                    [
                        (AllowedCredentialDefinition.creddef_author_did, cred_auth_did),
                        (AllowedCredentialDefinition.schema_issuer_did, schema_id[0]),
                        (AllowedCredentialDefinition.schema_name, schema_id[2]),
                        (AllowedCredentialDefinition.version, schema_id[3]),
                        (AllowedCredentialDefinition.tag, tag),
                        (AllowedCredentialDefinition.rev_reg_entry, True),
                    ],
                )
            case EndorseTransactionType.schema:
                logger.debug(
                    f">>> from is_endorsable_transaction: {trans} was a schema request"
                )
                schema = trans.transaction["data"]
                s = SchemaCriteria(trans.author_did, schema["name"], schema["version"])
                logger.debug(
                    f">>> from is_endorsable_transaction: {trans} with schema {s}"
                )
                return await allowed_schema(db, s)

            case EndorseTransactionType.cred_def:
                logger.debug(
                    f">>> from is_endorsable_transaction: {trans} was a cred_def request"
                )

                sequence_num: int = cast(int, trans.transaction.get("ref"))

                logger.debug(
                    f">>> from is_endorsable_transaction: {trans} awaiting schema"
                )
                response = cast(dict, await au.acapy_GET("schemas/" + str(sequence_num)))

                logger.debug(
                    f">>> from is_endorsable_transaction:\
                    {trans} was a cred_def request with response {response}"
                )
                schema_id: list[str] = response["schema"]["id"].split(":")
                return await allowed_creddef(
                    db,
                    CreddefCriteria(
                        DID=trans.author_did,
                        Schema_Issuer_DID=schema_id[0],
                        Schema_Name=schema_id[2],
                        Schema_Version=schema_id[3],
                        Tag=cast(str, trans.transaction.get("tag")),
                    ),
                )

        return False


async def auto_step_endorse_transaction_request_received(
    db: AsyncSession, payload: dict, handler_result: EndorseTransaction | dict
) -> EndorseTransaction | dict:
    """Handle incoming endorsement transaction requests with automatic processing."""
    logger.info(">>> in auto_step_endorse_transaction_request_received() ...")
    endorser_did = await get_endorser_did()
    transaction: EndorseTransaction = webhook_to_txn_object(payload, endorser_did)
    logger.debug(f">>> transaction = {transaction}")
    connection = await get_connection_object(db, transaction.connection_id)
    try:
        if is_auto_reject_connection(connection):
            logger.debug(
                ">>> from auto_step_endorse_transaction_request_received:\
                this was not"
            )
            handler_result = await reject_transaction(db, transaction)
        elif await is_auto_endorse_txn(db, transaction, connection):
            logger.debug(
                ">>> from auto_step_endorse_transaction_request_received:\
                this was allowed"
            )
            handler_result = await endorse_transaction(db, transaction)
        elif await is_endorsable_transaction(db, transaction):
            logger.debug(
                f">>> from auto_step_endorse_transaction_request_received:\
                {transaction} was allowed"
            )
            handler_result = await endorse_transaction(db, transaction)
        # If we could not auto endorse check if we should reject it or leave it pending
        elif await get_bool_config(db, "ENDORSER_REJECT_BY_DEFAULT"):
            handler_result = await reject_transaction(db, transaction)
        else:
            handler_result = {}
    except Exception as e:
        logger.error(traceback.format_exc())
        logger.error(
            f">>> in handle_endorse_transaction_request_received:\
            Failed to determine if the transaction should be endorsed with error: {e}"
        )
    return handler_result


async def auto_step_endorse_transaction_transaction_endorsed(
    db: AsyncSession, payload: dict, handler_result: dict
) -> dict:
    """Handle transaction endorsed events."""
    logger.info(">>> in auto_step_endorse_transaction_transaction_endorsed() ...")
    return {}


async def auto_step_endorse_transaction_transaction_refused(
    db: AsyncSession, payload: dict, handler_result: dict
) -> dict:
    """Handle transaction refused events."""
    logger.info(">>> in auto_step_endorse_transaction_transaction_refused() ...")
    return {}


async def auto_step_endorse_transaction_transaction_acked(
    db: AsyncSession, payload: dict, handler_result: dict
) -> dict:
    """Handle transaction acknowledgement events."""
    logger.info(">>> in auto_step_endorse_transaction_transaction_acked() ...")
    return {}


async def can_witness(db: AsyncSession, request: WitnessRequest) -> bool:
    """Determine if a request can be witnessed based on its type and attributes."""
    logger.debug(f">>> from can_witness {request.record_type}: entered")

    # Witnessing a log entry
    if request.record_type == "log-entry":
        did = request.record.get("state", {}).get("id", None)
        did_parts = did.split(":")
        return await allowed_log_entry(
            db,
            LogEntryCriteria(
                scid=did_parts[2],
                domain=did_parts[3],
                namespace=did_parts[4],
                identifier=did_parts[5],
            ),
        )

    # Witnessing an attested resource
    elif request.record_type == "attested-resource":
        resource_type = request.record.get("metadata", {}).get("resourceType", None)
        if resource_type == "anonCredsSchema":
            schema = request.record.get("content", {})
            return await allowed_schema(
                db,
                SchemaCriteria(
                    schema.get("issuerId", None),
                    schema.get("name", None),
                    schema.get("version", None),
                ),
            )
        elif resource_type == "anonCredsCredDef":
            cred_def = request.record.get("content", {})
            # TODO, resolve schema
            schema = await au.acapy_GET(
                "anoncreds/schema/" + cred_def.get("schemaId", None)
            )
            schema = schema.get("schema", {})
            return await allowed_creddef(
                db,
                CreddefCriteria(
                    DID=cred_def.get("issuerId", None),
                    Schema_Issuer_DID=schema.get("issuerId", None),
                    Schema_Name=schema.get("name", None),
                    Schema_Version=schema.get("version", None),
                    Tag=cred_def.get("tag", None),
                ),
            )
        elif resource_type == "anonCredsRevocRegDef":
            rev_reg_def = request.record.get("content", {})
            cred_def = await au.acapy_GET(
                "anoncreds/credential-definition/" + rev_reg_def.get("credDefId", None)
            )
            cred_def = cred_def.get("credential_definition", {})
            schema = await au.acapy_GET(
                "anoncreds/schema/" + cred_def.get("schemaId", None)
            )
            schema = schema.get("schema", {})
            return await check_auto_endorse(
                db,
                AllowedCredentialDefinition,
                [
                    (
                        AllowedCredentialDefinition.creddef_author_did,
                        cred_def.get("issuerId", None),
                    ),
                    (
                        AllowedCredentialDefinition.schema_issuer_did,
                        schema.get("issuerId", None),
                    ),
                    (AllowedCredentialDefinition.schema_name, schema.get("name", None)),
                    (AllowedCredentialDefinition.version, schema.get("version", None)),
                    (AllowedCredentialDefinition.tag, cred_def.get("tag", None)),
                    (AllowedCredentialDefinition.rev_reg_def, True),
                ],
            )
        elif resource_type == "anonCredsStatusList":
            rev_reg_entry = request.record.get("content", {})
            cred_def = await au.acapy_GET(
                "anoncreds/credential-definition/" + rev_reg_entry.get("credDefId", None)
            )
            cred_def = cred_def.get("credential_definition", {})
            schema = await au.acapy_GET(
                "anoncreds/schema/" + cred_def.get("schemaId", None)
            )
            schema = schema.get("schema", {})
            return await check_auto_endorse(
                db,
                AllowedCredentialDefinition,
                [
                    (
                        AllowedCredentialDefinition.creddef_author_did,
                        cred_def.get("issuerId", None),
                    ),
                    (
                        AllowedCredentialDefinition.schema_issuer_did,
                        schema.get("issuerId", None),
                    ),
                    (AllowedCredentialDefinition.schema_name, schema.get("name", None)),
                    (AllowedCredentialDefinition.version, schema.get("version", None)),
                    (AllowedCredentialDefinition.tag, cred_def.get("tag", None)),
                    (AllowedCredentialDefinition.rev_reg_def, True),
                ],
            )

        return False

    return False


async def auto_step_log_entry_pending(
    db: AsyncSession, payload: dict, handler_result: WitnessRequest | dict
) -> WitnessRequest | dict:
    """Handle incoming endorsement transaction requests with automatic processing."""
    logger.info(">>> in auto_step_log_entry_pending() ...")
    try:
        if await get_bool_config(db, "ENDORSER_AUTO_ENDORSE_REQUESTS"):
            logger.debug(
                ">>> from auto_step_log_entry_pending:\
                this was allowed"
            )
            handler_result = await witness_request(db, handler_result)
        elif await can_witness(db, handler_result):
            logger.debug(
                f">>> from auto_step_log_entry_pending:\
                {handler_result} was allowed"
            )
            handler_result = await witness_request(db, handler_result)
        # If we could not auto endorse check if we should reject it or leave it pending
        elif await get_bool_config(db, "ENDORSER_REJECT_BY_DEFAULT"):
            handler_result = await reject_request(db, handler_result)
        else:
            handler_result = {}
    except Exception as e:
        logger.error(traceback.format_exc())
        logger.error(
            f">>> in auto_step_log_entry_pending:\
            Failed to determine if the transaction should be endorsed with error: {e}"
        )
    return handler_result


async def auto_step_attested_resource_pending(
    db: AsyncSession, payload: dict, handler_result: WitnessRequest | dict
) -> WitnessRequest | dict:
    """Handle incoming endorsement transaction requests with automatic processing."""
    logger.info(">>> in auto_step_attested_resource_pending() ...")
    try:
        if await get_bool_config(db, "ENDORSER_AUTO_ENDORSE_REQUESTS"):
            logger.debug(
                ">>> from auto_step_attested_resource_pending:\
                this was allowed"
            )
            handler_result = await witness_request(db, handler_result)
        elif await can_witness(db, handler_result):
            logger.debug(
                f">>> from auto_step_attested_resource_pending:\
                {handler_result} was allowed"
            )
            handler_result = await witness_request(db, handler_result)
        # If we could not auto endorse check if we should reject it or leave it pending
        elif await get_bool_config(db, "ENDORSER_REJECT_BY_DEFAULT"):
            handler_result = await reject_request(db, handler_result)
        else:
            handler_result = {}
    except Exception as e:
        logger.error(traceback.format_exc())
        logger.error(
            f">>> in auto_step_attested_resource_pending:\
            Failed to determine if the transaction should be endorsed with error: {e}"
        )
    return handler_result
