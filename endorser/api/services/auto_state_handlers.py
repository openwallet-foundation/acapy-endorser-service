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

logger = logging.getLogger(__name__)


def is_auto_endorse_connection(connection: Connection) -> bool:
    # check if connection or author_did is setup for auto-endorse
    return (
        connection.author_status.name is AuthorStatusType.active.name
        and connection.endorse_status.name is EndorseStatusType.auto_endorse.name
    )


def is_auto_reject_connection(connection: Connection) -> bool:
    # check if connection or author_did is setup for auto-endorse
    return (
        connection.author_status.name is AuthorStatusType.active.name
        and connection.endorse_status.name is EndorseStatusType.auto_reject.name
    )


async def is_auto_endorse_txn(
    db: AsyncSession, transaction: EndorseTransaction, connection: Connection
):
    auto_req = await get_bool_config(db, "ENDORSER_AUTO_ENDORSE_REQUESTS")
    auto_req_type = await get_config(db, "ENDORSER_AUTO_ENDORSE_TXN_TYPES")
    if auto_req or is_auto_endorse_connection(connection):
        # auto-req is on, check if any txn types are configures
        if auto_req_type is None or len(auto_req_type) == 0:
            # nothing configured, auto-endorse-all
            return True
        txn_type = transaction.transaction_type
        auto_req_types = auto_req_type.split(",")
        return txn_type in auto_req_types

    return False


async def auto_step_ping_received(
    db: AsyncSession, payload: dict, handler_result: dict
) -> dict:
    return {}


async def auto_step_connections_request(
    db: AsyncSession, payload: dict, handler_result: dict
) -> dict | Connection:
    # auto-accept connection?
    connection: Connection = webhook_to_connection_object(payload)
    if await get_bool_config(db, "ENDORSER_AUTO_ACCEPT_CONNECTIONS"):
        result = await accept_connection_request(db, connection)
    return {}


async def auto_step_connections_response(
    db: AsyncSession, payload: dict, handler_result: dict
) -> dict:
    # no-op
    return {}


async def auto_step_connections_active(
    db: AsyncSession, payload: dict, handler_result: dict
) -> dict:
    # no-op
    return {}


async def auto_step_connections_completed(
    db: AsyncSession, payload: dict, handler_result: dict
) -> dict:
    # no-op
    return {}


@dataclass
class CreddefCriteria:
    DID: str
    Schema_Issuer_DID: str
    Schema_Name: str
    Schema_Version: str
    Tag: str


@dataclass
class SchemaCriteria:
    DID: str
    Name: str
    Version: str


def eq_or_wild(indb, clause: str | Any):
    if isinstance(clause, str):
        return or_(indb == clause, indb == "*")
    else:
        return indb == clause


async def check_auto_endorse(
    db: AsyncSession,
    table: type,
    filters: list[tuple[Any, Any]],
) -> bool:
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
    return await check_auto_endorse(
        db, AllowedPublicDid, [(AllowedPublicDid.registered_did, did)]
    )


async def allowed_schema(db: AsyncSession, schema_trans: SchemaCriteria) -> bool:
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


async def is_endorsable_transaction(
    db: AsyncSession, trans: EndorseTransaction
) -> bool:
    logger.debug(">>> from is_endorsable_transaction: entered")

    # Publishing/registering a public did on the ledger
    if (
        trans.author_goal_code == "aries.transaction.register_public_did"
        or trans.transaction_type == EndorseTransactionType.did
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
                    f">>> from is_endorsable_transaction: {trans} was a revocation registry"
                )
                # ex "3w88pmVPfeVaz8bMukH2uR:3:CL:81268:default"
                credDefId: list[str] = trans.transaction["credDefId"].split(":")
                cred_auth_did = credDefId[0]
                sequence_num = int(credDefId[3])
                tag = credDefId[4]

                logger.debug(
                    f">>> from is_endorsable_transaction: {trans} awaiting schema"
                )
                response = cast(
                    dict, await au.acapy_GET("schemas/" + str(sequence_num))
                )
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
                response = cast(
                    dict, await au.acapy_GET("schemas/" + str(sequence_num))
                )
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
                response = cast(
                    dict, await au.acapy_GET("schemas/" + str(sequence_num))
                )

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

            case EndorseTransactionType.attrib:
                logger.debug(
                    f">>> from is_endorsable_transaction: {trans} was an attrib request"
                )
                return True

        return False


# TODO look into returning the hander result
async def auto_step_endorse_transaction_request_received(
    db: AsyncSession, payload: dict, handler_result: EndorseTransaction | dict
) -> EndorseTransaction | dict:
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
    logger.info(">>> in auto_step_endorse_transaction_transaction_endorsed() ...")
    return {}


async def auto_step_endorse_transaction_transaction_refused(
    db: AsyncSession, payload: dict, handler_result: dict
) -> dict:
    logger.info(">>> in auto_step_endorse_transaction_transaction_refused() ...")
    return {}


async def auto_step_endorse_transaction_transaction_acked(
    db: AsyncSession, payload: dict, handler_result: dict
) -> dict:
    logger.info(">>> in auto_step_endorse_transaction_transaction_acked() ...")
    return {}
