"""FastAPI endpoints for managing and processing endorsement transactions.

This module provides APIs to list, retrieve, update, endorse, and reject transactions.
It uses an asynchronous SQLAlchemy session for database interactions and is designed
to work with a FastAPI router. It defines models such as EndorseTransaction and
EndorseTransactionList to structure responses, and handles errors by raising HTTP
exceptions with appropriate status codes.
"""

import logging
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from api.endpoints.dependencies.db import get_db
from api.endpoints.models.endorse import (
    EndorseTransaction,
    EndorseTransactionList,
    EndorseTransactionState,
)
from api.services.endorse import (
    get_transactions_list,
    get_transaction_object,
    endorse_transaction,
    reject_transaction,
)
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR
from api.endpoints.dependencies.jwt_security import check_access_token


router = APIRouter(tags=["endorse"], dependencies=[Depends(check_access_token)])
logger = logging.getLogger(__name__)


@router.get(
    "/transactions",
    status_code=status.HTTP_200_OK,
    response_model=EndorseTransactionList,
)
async def get_transactions(
    transaction_state: EndorseTransactionState | None = None,
    connection_id: str | None = None,
    page_size: int = 10,
    page_num: int = 1,
    db: AsyncSession = Depends(get_db),
) -> EndorseTransactionList:
    """Retrieve a list of transactions based on filtering criteria.

    Args:
        transaction_state (EndorseTransactionState | None): The state of the transaction.
        connection_id (str | None): The ID of the connection.
        page_size (int): The number of transactions per page.
        page_num (int): The current page number.
        db (AsyncSession): The database session.

    Returns:
        EndorseTransactionList: A list of transactions with pagination info.

    Raises:
        HTTPException: If there is any error during transaction retrieval.
    """
    try:
        (total_count, transactions) = await get_transactions_list(
            db,
            transaction_state=transaction_state.value if transaction_state else None,
            connection_id=connection_id,
            page_size=page_size,
            page_num=page_num,
        )
        response: EndorseTransactionList = EndorseTransactionList(
            page_size=page_size,
            page_num=page_num,
            count=len(transactions),
            total_count=total_count,
            transactions=transactions,
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get(
    "/transactions/{transaction_id}",
    status_code=status.HTTP_200_OK,
    response_model=EndorseTransaction,
)
async def get_transaction(
    transaction_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> EndorseTransaction:
    """Retrieve a transaction by its ID."""
    try:
        transaction = await get_transaction_object(db, transaction_id)
        return transaction
    except Exception as e:
        raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.put(
    "/transactions/{transaction_id}",
    status_code=status.HTTP_200_OK,
    response_model=EndorseTransaction,
)
async def update_transactions(
    transaction_id: str,
    meta_data: dict,
    db: AsyncSession = Depends(get_db),
) -> EndorseTransaction:
    """Update meta-data (tags) on a transaction.

    Args:
        transaction_id (str): The ID of the transaction to update.
        meta_data (dict): The metadata to be updated on the transaction.
        db (AsyncSession): The database session.

    Returns:
        EndorseTransaction: The updated transaction data.
    """
    raise NotImplementedError


@router.post(
    "/transactions/{transaction_id}/endorse",
    status_code=status.HTTP_200_OK,
    response_model=EndorseTransaction,
)
async def endorse_transaction_endpoint(
    transaction_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> EndorseTransaction:
    """Manually approve an endorsement.

    This endpoint allows for the manual approval of a transaction's endorsement using
    the provided transaction ID. It will retrieve the transaction from the database
    and endorse it. Returns the endorsed transaction if successful.

    Args:
        transaction_id (UUID): Unique identifier for the transaction.
        db (AsyncSession): Database session dependency.

    Returns:
        EndorseTransaction: The endorsed transaction object.

    Raises:
        HTTPException: If an error occurs during processing.
    """
    try:
        transaction: EndorseTransaction = await get_transaction_object(db, transaction_id)
        endorsed_txn = await endorse_transaction(db, transaction)
        return endorsed_txn
    except Exception as e:
        raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post(
    "/transactions/{transaction_id}/reject",
    status_code=status.HTTP_200_OK,
    response_model=EndorseTransaction,
)
async def reject_transaction_endpoint(
    transaction_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> EndorseTransaction:
    """Rejects an endorsement transaction.

    This endpoint allows for the manual rejection of an endorsement transaction
    identified by the provided transaction ID.

    Args:
        transaction_id (UUID): The unique identifier of the transaction to reject.
        db (AsyncSession, optional): The database session dependency.

    Returns:
        EndorseTransaction: The rejected endorsement transaction object.

    Raises:
        HTTPException: If an error occurs during processing, an HTTP 500 error is raised
                       with the error detail.
    """
    try:
        transaction: EndorseTransaction = await get_transaction_object(db, transaction_id)
        rejected_txn = await reject_transaction(db, transaction)
        return rejected_txn
    except Exception as e:
        raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
