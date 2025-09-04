"""Module for handling webvh witnessing in the Aries Endorser Service."""

import logging
import json
from pydantic import BaseModel

from api.db.models.witness_request import WitnessRequestDbRecord

logger = logging.getLogger(__name__)


class WitnessRequest(BaseModel):
    """Represent a witnessing request."""

    scid: str
    state: str
    record: dict
    record_id: str
    record_type: str
    created_at: str | None = None


def webhook_to_witness_object(payload: dict) -> WitnessRequest:
    """Convert from a webhook payload to a witness request."""
    logger.debug(f">>> from payload: {payload}")
    request: WitnessRequest = WitnessRequest(
        scid=payload.get("scid"),
        state=payload.get("state"),
        record=payload.get("record"),
        record_id=payload.get("record_id"),
        record_type=payload.get("record_type"),
    )
    logger.debug(f">>> to witness request: {request}")
    return request


def request_to_db_object(request: WitnessRequest) -> WitnessRequestDbRecord:
    """Convert from model object to database model object."""
    logger.debug(f">>> from request: {request}")
    if request.record_type == "log-entry":
        did = request.record.get("state", {}).get("id", None)
    elif request.record_type == "attested-resource":
        did = request.record.get("id", "").split("/")[0]
    else:
        logger.error(f"Unexpected record_type: {request.record_type}")
        raise ValueError(f"Unexpected record_type: {request.record_type}")
    did_parts = did.split(":")
    (scid, domain, namespace, identifier) = (
        did_parts[2],
        did_parts[3],
        did_parts[4],
        did_parts[5],
    )
    if scid != request.scid:
        logger.warning(
            f"Data inconsistency: derived scid '{scid}' \
                does not match request.scid '{request.scid}'"
        )
    db_record: WitnessRequestDbRecord = WitnessRequestDbRecord(
        scid=scid,
        domain=domain,
        namespace=namespace,
        identifier=identifier,
        state=request.state,
        record=json.dumps(request.record),
        record_id=request.record_id,
        record_type=request.record_type,
    )
    logger.debug(f">>> to request: {db_record}")
    return db_record


def db_to_request_object(db_record: WitnessRequestDbRecord) -> WitnessRequest:
    """Convert from database and acapy objects to model object."""
    request: WitnessRequest = WitnessRequest(
        scid=db_record.scid,
        state=db_record.state,
        record=json.loads(db_record.record),
        record_id=db_record.record_id,
        record_type=db_record.record_type,
    )
    return request
