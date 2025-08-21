"""This module provides functions for managing witness requests with a database."""

import logging
from typing import cast

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

import api.acapy_utils as au
from api.db.errors import DoesNotExist
from api.db.models.witness_request import WitnessRequestDbRecord
from api.endpoints.models.witness import (
    WitnessRequest,
    request_to_db_object,
)

logger = logging.getLogger(__name__)


async def db_add_db_txn_record(db: AsyncSession, db_request: WitnessRequestDbRecord):
    """Add a new transaction record to the database."""
    db.add(db_request)
    await db.commit()


async def db_fetch_db_txn_record(
    db: AsyncSession, record_id: str
) -> WitnessRequestDbRecord:
    """Fetch a single transaction record from the database by ID."""
    logger.info(f">>> db_fetch_db_txn_record() for {record_id}")
    q = select(WitnessRequestDbRecord).where(
        WitnessRequestDbRecord.record_id == record_id
    )
    result = await db.execute(q)
    result_rec = result.scalar_one_or_none()
    if not result_rec:
        raise DoesNotExist(
            f"{WitnessRequest.__name__}<record_id:{record_id}> does not exist"
        )
    return result_rec


async def db_update_db_txn_record(
    db: AsyncSession, db_record: WitnessRequestDbRecord
) -> WitnessRequestDbRecord:
    """Update an existing transaction record in the database."""
    payload_dict = db_record.dict()
    q = (
        update(WitnessRequestDbRecord)
        .where(WitnessRequestDbRecord.record_id == db_record.record_id)
        .values(payload_dict)
    )
    await db.execute(q)
    await db.commit()
    return await db_fetch_db_txn_record(db, db_record.record_id)


async def store_witness_request(db: AsyncSession, request: WitnessRequest):
    """Store a new witness request in the database."""
    logger.info(f">>> called store_witness_request with: {request.record_id}")

    db_record: WitnessRequestDbRecord = request_to_db_object(request)
    await db_add_db_txn_record(db, db_record)
    logger.info(f">>> stored witness_request: {db_record.record_id}")

    return request


async def update_witnessing_status(db: AsyncSession, request: WitnessRequest):
    """Update the status of an witnessing request."""
    logger.info(f">>> called update_witnessing_status with: {request.record_id}")

    # fetch existing db object
    db_record: WitnessRequestDbRecord = await db_fetch_db_txn_record(
        db, request.record_id
    )

    # update local db state
    db_record.state = request.state
    db_record = await db_update_db_txn_record(db, db_record)
    logger.info(
        f">>> updated witness_request for {db_record.record_id} {db_record.state}"
    )

    return request


async def witness_request(db: AsyncSession, request: WitnessRequest):
    """Witness a request and update its status."""
    logger.info(f">>> called witness_request with: {request.record_id}")

    # fetch existing db object
    db_record: WitnessRequestDbRecord = await db_fetch_db_txn_record(
        db, request.record_id
    )

    # witness request and tell aca-py
    if request.record_type == "log-entry":
        cast(
            dict,
            await au.acapy_POST(f"did/webvh/witness/log-entries?scid={request.scid}"),
        )
    elif request.record_type == "attested-resource":
        cast(
            dict,
            await au.acapy_POST(
                f"did/webvh/witness/attested-resources?scid={request.scid}"
            ),
        )

    # update local db state
    db_record.state = "witnessed"
    db_record = await db_update_db_txn_record(db, db_record)
    logger.info(f">>> endorsed endorser_request for {db_record.record_id}")

    return db_record


async def reject_request(db: AsyncSession, request: WitnessRequest):
    """Reject a transaction and update its status."""
    logger.info(f">>> called reject_request with: {request.record_id}")

    # fetch existing db object
    db_record: WitnessRequestDbRecord = await db_fetch_db_txn_record(
        db, request.record_id
    )

    # reject request and tell aca-py
    if request.record_type == "log-entry":
        cast(
            dict,
            await au.acapy_DELETE(f"did/webvh/witness/log-entries?scid={request.scid}"),
        )
    elif request.record_type == "attested-resource":
        cast(
            dict,
            await au.acapy_DELETE(
                f"did/webvh/witness/attested-resources?scid={request.scid}"
            ),
        )

    # update local db state
    db_record.state = "rejected"
    db_record = await db_update_db_txn_record(db, db_record)
    logger.info(f">>> rejected witness_request for {request.record_id}")

    return db_record
