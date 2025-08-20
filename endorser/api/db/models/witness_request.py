"""WitnessRequest Database Tables/Models."""

import uuid
from datetime import datetime
from typing import List, Optional

from sqlmodel import Field
from sqlalchemy import Column, func, text, String
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP, ARRAY

from api.db.models.base import BaseModel


class WitnessRequestDbRecord(BaseModel, table=True):
    """WitnessRequestDbRecord.

    This is the model for the EndorseRequest table
    (postgresql specific dialects in use).

    Attributes:
      witness_request_id: Endorser's EndorseRequest ID
      author_goal_code: Authors Goal for this transaction
      contact_id: Endorser's Contact ID
      transaction_id: Underlying AcaPy transaction_id id
      connection_id: Underlying AcaPy connection id
      state: The underlying AcaPy transaction state
      created_at: Timestamp when record was created
      updated_at: Timestamp when record was last modified
    """

    witness_request_id: uuid.UUID = Field(
        sa_column=Column(
            UUID(as_uuid=True),
            primary_key=True,
            server_default=text("gen_random_uuid()"),
        )
    )
    state: str = Field(nullable=True, default=None)
    record: str = Field(nullable=True, default=None)
    record_id: uuid.UUID = Field(nullable=False)
    record_type: str = Field(nullable=False)
    scid: str = Field(nullable=False)
    domain: str = Field(nullable=False)
    namespace: str = Field(nullable=False)
    identifier: str = Field(nullable=False)

    created_at: datetime = Field(
        sa_column=Column(TIMESTAMP, nullable=False, server_default=func.now())
    )
    updated_at: datetime = Field(
        sa_column=Column(
            TIMESTAMP, nullable=False, server_default=func.now(), onupdate=func.now()
        )
    )