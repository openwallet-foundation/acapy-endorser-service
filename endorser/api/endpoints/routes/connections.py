"""API endpoints for managing connections in the Aries Endorser Service."""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR

from api.endpoints.dependencies.db import get_db
from api.endpoints.models.connections import (
    AuthorStatusType,
    Connection,
    ConnectionList,
    ConnectionStateType,
    EndorseStatusType,
)
from api.services.connections import (
    accept_connection_request,
    get_connection_object,
    get_connections_list,
    update_connection_config,
    update_connection_info,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=ConnectionList)
async def get_connections(
    connection_state: Optional[ConnectionStateType] = None,
    page_size: int = 10,
    page_num: int = 1,
    db: AsyncSession = Depends(get_db),
) -> ConnectionList:
    """Retrieve a paginated list of connections based on state.

    Args:
        connection_state ConnectionStateType: Desired state to filter connections.
        page_size int: Number of connections per page.
        page_num int: Desired page number.
        db AsyncSession: Database session.

    Returns:
        ConnectionList: An object containing a list of connections and pagination details.

    Raises:
        HTTPException: If there is an error retrieving connections.
    """
    try:
        (total_count, connections) = await get_connections_list(
            db,
            connection_state=connection_state.value if connection_state else None,
            page_size=page_size,
            page_num=page_num,
        )
        response: ConnectionList = ConnectionList(
            page_size=page_size,
            page_num=page_num,
            count=len(connections),
            total_count=total_count,
            connections=connections,
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{connection_id}", response_model=Connection)
async def get_connection(
    connection_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> Connection:
    """Retrieve a connection by its ID.

    Parameters:
    - connection_id: Unique identifier for the connection.
    - db: Database session dependency.

    Returns:
    - A Connection object.

    Raises:
    - HTTPException: If there is a server error.
    """
    try:
        connection = await get_connection_object(db, connection_id)
        return connection
    except Exception as e:
        raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.put("/{connection_id}", response_model=Connection)
async def update_connection(
    connection_id: UUID,
    alias: str,
    public_did: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> Connection:
    """Update a connection's information based on the connection_id.

    Args:
        connection_id (UUID): Unique identifier for the connection.
        alias (str): New alias for the connection.
        public_did (str | None, optional): Optional public DID associated
                                          with the connection.
        db (AsyncSession, optional): The database session. Defaults to
                                     dependency injection with get_db.

    Returns:
        Connection: The updated connection object.

    Raises:
        HTTPException: If there is an error updating the connection.
    """
    try:
        connection = await update_connection_info(db, connection_id, alias, public_did)
        return connection
    except Exception as e:
        raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.put("/{connection_id}/configure", response_model=Connection)
async def configure_connection(
    connection_id: UUID,
    author_status: AuthorStatusType,
    endorse_status: EndorseStatusType,
    db: AsyncSession = Depends(get_db),
) -> Connection:
    """Configure the connection with author and endorse statuses.

    Args:
        connection_id (UUID): Unique identifier for the connection.
        author_status (AuthorStatusType): The status of the author.
        endorse_status (EndorseStatusType): The endorsement status.
        db (AsyncSession, optional): The database session.

    Returns:
        Connection: The updated connection configuration.

    Raises:
        HTTPException: If an error occurs during the configuration update.
    """
    try:
        connection = await update_connection_config(
            db, connection_id, author_status, endorse_status
        )
        return connection
    except Exception as e:
        raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/{connection_id}/accept", response_model=Connection)
async def accept_connection(
    connection_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> Connection:
    """Manually accept a connection."""
    try:
        connection: Connection = await get_connection_object(db, connection_id)
        accepted_connection = await accept_connection_request(db, connection)
        return accepted_connection
    except Exception as e:
        raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/{connection_id}/reject", response_model=Connection)
async def reject_connection(
    connection_id: str,
    db: AsyncSession = Depends(get_db),
) -> Connection:
    """Reject a connection request.

    This endpoint will be used to reject a connection by its ID.
    Currently raises a NotImplementedError as the ProblemReport
    response is not yet implemented.

    Parameters:
    - connection_id: str - The ID of the connection to be rejected.
    - db: AsyncSession - Database session dependency.

    Returns:
    - Connection: The rejected connection data.
    """
    # TODO this should send a ProblemReport back to the requester
    raise NotImplementedError
