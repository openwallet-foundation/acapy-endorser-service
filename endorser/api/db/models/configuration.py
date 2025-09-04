"""Configuration Database Tables/Models.

Models of the Endorser tables for API configuration.

"""

import uuid
from datetime import datetime

from sqlmodel import Field
from sqlalchemy import Column, func, text
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP

from api.db.models.base import BaseModel


class ConfigurationDB(BaseModel, table=True):
    """Configuration.

    This is the model for the Configuration table (postgresql specific dialects in use).

    Attributes:
      config_id: Config Item ID
      config_name: Name of the config item
      config_value: Value of the config item
      created_at: Timestamp when record was created
      updated_at: Timestamp when record was last modified
    """

    config_id: uuid.UUID = Field(
        sa_column=Column(
            UUID(as_uuid=True),
            primary_key=True,
            server_default=text("gen_random_uuid()"),
        )
    )

    config_name: str = Field(nullable=False)
    config_value: str = Field(nullable=False)

    created_at: datetime = Field(
        sa_column=Column(TIMESTAMP, nullable=False, server_default=func.now())
    )
    updated_at: datetime = Field(
        sa_column=Column(
            TIMESTAMP, nullable=False, server_default=func.now(), onupdate=func.now()
        )
    )
