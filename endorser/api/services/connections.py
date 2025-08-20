"""This module provides database operations for to connections in the Endorser service.

Key functionalities include adding, fetching, updating, and retrieving
connection records while leveraging SQLAlchemy's asynchronous
capabilities.

"""

import logging
from typing import cast
from uuid import UUID

from sqlalchemy import desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.functions import func

import api.acapy_utils as au
from api.db.errors import DoesNotExist
from api.db.models.contact import Contact
from api.endpoints.models.connections import (
    AuthorStatusType,
    Connection,
    ConnectionProtocolType,
    EndorseStatusType,
    connection_to_db_object,
    db_to_connection_object,
)
from api.endpoints.models.endorse import (
    EndorserRoleType,
)

logger = logging.getLogger(__name__)


async def db_add_db_contact_record(db: AsyncSession, db_contact: Contact):
    """Add a contact record to the database."""
    logger.debug(f">>> adding contact: {db_contact} ...")
    db.add(db_contact)
    await db.commit()


async def db_fetch_db_contact_record(db: AsyncSession, connection_id: UUID) -> Contact:
    """Fetch a contact record from the database for the given connection ID.

    Args:
        db (AsyncSession): The database session to use for the query.
        connection_id (UUID): The ID of the connection to fetch the contact record for.

    Raises:
        DoesNotExist: If no contact record exists for the provided connection ID.

    Returns:
        Contact: The contact record associated with the given connection ID.
    """
    logger.info(f">>> db_fetch_db_contact_record() for {connection_id}")
    q = select(Contact).where(Contact.connection_id == connection_id)
    result = await db.execute(q)
    result_rec = result.scalar_one_or_none()
    if not result_rec:
        raise DoesNotExist(
            f"{Contact.__name__}<connection_id:{connection_id}> does not exist"
        )
    return result_rec


async def db_update_db_contact_record(db: AsyncSession, db_contact: Contact) -> Contact:
    """Update a contact record in the database and return the updated contact.

    Parameters:
        db (AsyncSession): The database session to use for the update.
        db_contact (Contact): The contact object containing updated information.

    Returns:
        Contact: The updated contact record from the database.
    """
    payload_dict = db_contact.dict()
    q = (
        update(Contact)
        .where(Contact.contact_id == db_contact.contact_id)
        .where(Contact.connection_id == db_contact.connection_id)
        .values(payload_dict)
    )
    await db.execute(q)
    await db.commit()
    return await db_fetch_db_contact_record(db, db_contact.connection_id)


async def db_get_contact_records(
    db: AsyncSession,
    state: str | None = None,
    page_size: int = 10,
    page_num: int = 1,
) -> tuple[int, list[Contact]]:
    """Retrieve paginated contact records filtered by state."""
    limit = page_size
    skip = (page_num - 1) * limit
    filters = []
    if state:
        filters.append(Contact.state == state)

    # build out a base query with all filters
    base_q = select(Contact).filter(*filters)

    # get a count of ALL records matching our base query
    count_q = base_q.with_only_columns(func.count()).order_by(None)
    count_q_rec = await db.execute(count_q)
    total_count = cast(int, count_q_rec.scalar())

    # add in our paging and ordering to get the result set
    results_q = base_q.limit(limit).offset(skip).order_by(desc(Contact.created_at))

    results_q_recs = await db.execute(results_q)
    db_connections: list[Contact] = results_q_recs.scalars().all()

    return (total_count, db_connections)


async def get_connections_list(
    db: AsyncSession,
    connection_state: str | None = None,
    page_size: int = 10,
    page_num: int = 1,
) -> tuple[int, list[Connection]]:
    """Retrieve a paginated list of connections from the database."""

    (count, db_contacts) = await db_get_contact_records(
        db,
        state=connection_state,
        page_size=page_size,
        page_num=page_num,
    )
    items = []
    for db_contact in db_contacts:
        item = db_to_connection_object(db_contact, acapy_connection=None)
        items.append(item)
    return (count, items)


async def get_connection_object(
    db: AsyncSession,
    connection_id: UUID,
) -> Connection:
    """Retrieve a connection object based on the provided connection ID.

    Args:
        db (AsyncSession): The database session to use for the query.
        connection_id (UUID): The ID of the connection to retrieve.

    Returns:
        Connection: The corresponding connection object.
    """
    logger.info(f">>> get_connection_object() for {connection_id}")
    db_contact: Contact = await db_fetch_db_contact_record(db, connection_id)
    item = db_to_connection_object(db_contact, acapy_connection=None)
    return item


async def store_connection_request(
    db: AsyncSession, connection: Connection
) -> Connection:
    """Store a connection request in the database.

    Args:
        db (AsyncSession): The database session for async operations.
        connection (Connection): The connection object to be stored.

    Returns:
        Connection: The original connection object.
    """
    logger.info(f">>> called store_connection_request with: {connection.connection_id}")

    db_contact: Contact = connection_to_db_object(connection)
    await db_add_db_contact_record(db, db_contact)
    logger.info(f">>> stored connection: {db_contact.connection_id}")

    return connection


async def accept_connection_request(
    db: AsyncSession, connection: Connection
) -> Connection:
    """Accepts a connection request and updates the corresponding database record."""
    logger.info(f">>> called accept_connection_request with: {connection.connection_id}")

    # fetch existing db object
    db_contact: Contact = await db_fetch_db_contact_record(db, connection.connection_id)

    # accept connection
    if connection.connection_protocol == ConnectionProtocolType.DIDExchange.value:
        await au.acapy_POST(
            f"didexchange/{connection.connection_id}/accept-request",
        )

    # update local db state
    db_contact.state = connection.state
    db_contact = await db_update_db_contact_record(db, db_contact)
    logger.info(
        f">>> accepted connection for {connection.connection_id} {db_contact.state}"
    )

    # set author meta-data on this connection
    await au.acapy_POST(
        f"transactions/{connection.connection_id}/set-endorser-role",
        params={"transaction_my_job": "TRANSACTION_ENDORSER"},
    )

    return connection


async def update_connection_status(
    db: AsyncSession, connection: Connection
) -> Connection:
    """Update the status of a connection in the database."""
    logger.debug(f">>> called update_connection_status with: {connection.connection_id}")

    # fetch existing db object
    db_contact: Contact = await db_fetch_db_contact_record(db, connection.connection_id)

    # update local db state
    db_contact.state = connection.state
    db_contact = await db_update_db_contact_record(db, db_contact)
    logger.debug(
        f">>> updated connection for {connection.connection_id} {db_contact.state}"
    )

    return connection


async def set_connection_author_metadata(
    db: AsyncSession, connection: Connection
) -> dict:
    """Set the endorser role metadata for a connection if not already set."""
    # confirm if we have already set the role on this connection
    connection_id = connection.connection_id
    logger.info(f">>> check for metadata on connection: {connection_id}")
    conn_meta_data = cast(
        dict, await au.acapy_GET(f"connections/{connection_id}/metadata")
    )
    if "transaction-jobs" in conn_meta_data["results"]:
        if "transaction_my_job" in conn_meta_data["results"]["transaction-jobs"]:
            return {}

    # set our endorser role
    params = {"transaction_my_job": EndorserRoleType.Endorser.value}
    logger.info(
        f">>> Setting meta-data for connection: {Connection}, with params: {params}"
    )
    await au.acapy_POST(f"transactions/{connection_id}/set-endorser-role", params=params)
    return {}


async def update_connection_info(
    db: AsyncSession, connection_id: UUID, alias: str, public_did: str | None = None
):
    """Update the connection information for a specific contact."""
    # fetch existing db object
    db_contact: Contact = await db_fetch_db_contact_record(db, connection_id)
    db_contact.connection_alias = alias
    if public_did:
        db_contact.public_did = public_did
    db_contact = await db_update_db_contact_record(db, db_contact)
    connection = db_to_connection_object(db_contact, acapy_connection=None)
    return connection


async def update_connection_config(
    db: AsyncSession,
    connection_id: UUID,
    author_status: AuthorStatusType,
    endorse_status: EndorseStatusType,
):
    """Update the configuration for a connection in the database."""
    # fetch existing db object
    db_contact: Contact = await db_fetch_db_contact_record(db, connection_id)
    db_contact.author_status = author_status.value
    db_contact.endorse_status = endorse_status.value
    db_contact = await db_update_db_contact_record(db, db_contact)
    connection = db_to_connection_object(db_contact, acapy_connection=None)
    return connection
