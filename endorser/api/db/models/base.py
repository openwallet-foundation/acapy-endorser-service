"""Defines base classes for schemas and ORM models with common fields and configurations.

This module provides foundational classes using SQLModel and
Pydantic. The base classes define UUID, created_at, and updated_at
fields, which are automatically generated and managed on the server
side.

"""

import uuid
from datetime import datetime
from typing import Optional

import pydantic
from pydantic_settings import SettingsConfigDict
from sqlalchemy import Column, func, text
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlmodel import Field, SQLModel


class BaseSchema(pydantic.BaseModel):
    """Base schema model configured to support ORM mode and attribute reading.

    The BaseSchema class inherits from Pydantic's BaseModel and is configured with
    SettingsConfigDict to enable reading with ORM mode and from_attributes options.
    """

    model_config = SettingsConfigDict(from_attributes=True, read_with_orm_mode=True)


class BaseModel(SQLModel, BaseSchema):
    """BaseModel class that combines SQLModel and BaseSchema.

    This class is configured with eager loading of default values.
    """

    __mapper_args__ = {"eager_defaults": True}


class BaseTable(BaseModel):
    """BaseTable model with optional server-generated fields for table entities.

    Attributes:
        id (Optional[uuid.UUID]): Unique identifier for the record, generated on
            the server. Defaults to None.
        created_at (Optional[datetime]): Timestamp for when the record was created,
            generated on the server. Defaults to None.
        updated_at (Optional[datetime]): Timestamp for when the record was last
            updated, auto-updated on the server. Defaults to None.
    """

    # the following are marked optional because they are generated on the server
    # these will be included in each class where we set table=true (our table classes)
    id: Optional[uuid.UUID] = Field(
        None,
        sa_column=Column(
            UUID(as_uuid=True),
            primary_key=True,
            server_default=text("gen_random_uuid()"),
        ),
    )
    created_at: Optional[datetime] = Field(
        None, sa_column=Column(TIMESTAMP, nullable=False, server_default=func.now())
    )
    updated_at: Optional[datetime] = Field(
        None,
        sa_column=Column(
            TIMESTAMP, nullable=False, server_default=func.now(), onupdate=func.now()
        ),
    )
