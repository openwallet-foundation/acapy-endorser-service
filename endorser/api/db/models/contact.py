"""Contact Database Tables/Models.

Models of the Endorser tables for Contacts (Authors) and related data.
"""

import uuid
from datetime import datetime
from typing import List

from sqlmodel import Field
from sqlalchemy import Column, func, text, String
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP, ARRAY

from api.db.models.base import BaseModel


class Contact(BaseModel, table=True):
    """Contact is the model for the Contact table (postgresql specific dialects in use).

    Attributes:
      contact_id: Endorser's Contact ID
      author_status: Whether they are an approved author or not
      endorse_status: Whether endorsements are auto-approved or not
      tags: Set by endorser for arbitrary grouping of Contacts
      connection_id: Underlying AcaPy connection id
      connection_alias: Underlying AcaPy connection alias
      public_did: Represents the Contact's agent's Public DID (if any)
      state: The underlying AcaPy connection state
      created_at: Timestamp when record was created
      updated_at: Timestamp when record was last modified.
    """

    contact_id: uuid.UUID = Field(
        sa_column=Column(
            UUID(as_uuid=True),
            primary_key=True,
            server_default=text("gen_random_uuid()"),
        )
    )

    author_status: str = Field(nullable=False)
    endorse_status: str = Field(nullable=False)
    tags: List[str] = Field(sa_column=Column(ARRAY(String)))

    # acapy data ---
    connection_id: uuid.UUID = Field(sa_column=Column(UUID(as_uuid=True), unique=True))
    connection_protocol: str = Field(nullable=False)
    connection_alias: str = Field(nullable=True, default=None)
    public_did: str = Field(nullable=True, default=None)
    state: str = Field(nullable=False)
    their_label: str = Field(nullable=False)
    # --- acapy data

    created_at: datetime = Field(
        sa_column=Column(TIMESTAMP, nullable=False, server_default=func.now())
    )
    updated_at: datetime = Field(
        sa_column=Column(
            TIMESTAMP, nullable=False, server_default=func.now(), onupdate=func.now()
        )
    )
