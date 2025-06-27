"""This module defines connection-related models and utility functions.

Includes models for connections, enums for various connection states, roles,
and status types, and functions to convert between webhook payloads,
Connection objects, and database models. Additionally, it logs the conversion process.
"""

import logging
from enum import Enum
from uuid import UUID

from api.db.models.base import BaseModel
from api.db.models.contact import Contact

logger = logging.getLogger(__name__)


class ConnectionProtocolType(str, Enum):
    """Enumeration for connection protocol types."""

    Connections = "connections/1.0"
    DIDExchange = "didexchange/1.0"


class ConnectionStateType(str, Enum):
    """Enumeration for connection state types."""

    start = "start"
    init = "init"
    invitation = "invitation"
    request = "request"
    response = "response"
    active = "active"
    completed = "completed"
    abandoned = "abandoned"
    error = "error"


class ConnectionRoleType(str, Enum):
    """Enumeration for connection role types."""

    inviter = "inviter"
    invitee = "invitee"
    requester = "requester"
    responder = "responder"


class AuthorStatusType(str, Enum):
    """Enumeration for author status types."""

    active = "Active"
    suspended = "Suspended"


class EndorseStatusType(str, Enum):
    """Enumeration for endorsement status types."""

    auto_endorse = "AutoEndorse"
    manual_endorse = "ManualEndorse"
    auto_reject = "AutoReject"


class Connection(BaseModel):
    """Model for representing a connection."""

    connection_id: UUID
    alias: str | None = None
    author_status: AuthorStatusType
    endorse_status: EndorseStatusType
    tags: list[str]
    created_at: str | None = None
    updated_at: str | None = None
    state: str
    connection_protocol: str
    error_msg: str | None = None
    invitation: str | None = None
    my_did: str | None = None
    their_did: str | None = None
    their_label: str | None = None
    their_public_did: str | None = None
    their_role: str | None = None


class ConnectionList(BaseModel):
    """Model for representing a paginated list of connections."""

    page_size: int
    page_num: int
    count: int
    total_count: int
    connections: list[Connection]


def webhook_to_connection_object(payload: dict) -> Connection:
    """Convert from a webhook payload to a connection."""
    logger.debug(f">>> from payload: {payload}")
    connection: Connection = Connection(
        connection_id=UUID(payload.get("connection_id")),
        alias=payload.get("alias"),
        author_status=AuthorStatusType.active,
        endorse_status=EndorseStatusType.manual_endorse,
        tags=[],
        state=str(payload.get("state")),
        connection_protocol=str(payload.get("connection_protocol")),
        error_msg=payload.get("error_msg"),
        invitation=payload.get("invitation"),
        my_did=payload.get("my_did"),
        their_did=payload.get("their_did"),
        their_label=payload.get("their_label"),
        their_public_did=payload.get("their_public_did"),
        their_role=payload.get("their_role"),
    )
    logger.debug(f">>> to connection: {connection}")
    return connection


def connection_to_db_object(connection: Connection) -> Contact:
    """Convert from model object to database model object."""
    logger.debug(f">>> from connection: {connection}")
    contact: Contact = Contact(
        author_status=connection.author_status,
        endorse_status=connection.endorse_status,
        tags=connection.tags,
        connection_id=connection.connection_id,
        connection_protocol=connection.connection_protocol,
        public_did=connection.their_public_did if connection.their_public_did else "",
        state=connection.state,
        connection_alias=connection.alias if connection.alias else "",
        their_label=connection.their_label,
    )
    logger.debug(f">>> to contact: {contact}")
    return contact


def db_to_connection_object(
    contact: Contact, acapy_connection: dict | None = None
) -> Connection:
    """Convert from database and acapy objects to model object."""
    connection: Connection = Connection(
        author_status=AuthorStatusType(contact.author_status),
        endorse_status=EndorseStatusType(contact.endorse_status),
        tags=contact.tags,
        connection_id=contact.connection_id,
        connection_protocol=contact.connection_protocol,
        their_public_did=contact.public_did,
        state=contact.state,
        alias=contact.connection_alias,
        their_label=contact.their_label,
        created_at=str(contact.created_at),
        updated_at=str(contact.updated_at),
    )
    if acapy_connection:
        connection.error_msg = acapy_connection.get("error_msg")
        connection.invitation = acapy_connection.get("invitation")
        connection.my_did = acapy_connection.get("my_did")
        connection.their_label = acapy_connection.get("their_label")
        connection.their_role = acapy_connection.get("their_role")
    return connection
