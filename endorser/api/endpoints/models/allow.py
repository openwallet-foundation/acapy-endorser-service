"""Models for paginated lists of allowed items in the Endorser Service API.

This module defines Pydantic models used to represent paginated lists of
allowed public DIDs, schemas, and credential definitions. These models
facilitate API responses by providing structured data and support for
pagination.

Classes:
- AllowedPublicDidList: Represents a paginated list of allowed public DIDs.
- AllowedSchemaList: Represents a paginated list of allowed schemas.
- AllowedCredentialDefinitionList: Represents a paginated list of allowed
  credential definitions.
"""

import logging

from pydantic import BaseModel

from api.db.models.allow import (
    AllowedPublicDid,
    AllowedSchema,
    AllowedCredentialDefinition,
    AllowedLogEntry,
)


logger = logging.getLogger(__name__)


class AllowedPublicDidList(BaseModel):
    """Represents a paginated list of allowed public DIDs.

    Attributes:
        page_size (int): The number of items per page.
        page_num (int): The current page number.
        count (int): The number of items in the current page.
        total_count (int): The total number of items across all pages.
        dids (list[AllowedPublicDid]): The list of allowed public DIDs.
    """

    page_size: int
    page_num: int
    count: int
    total_count: int
    dids: list[AllowedPublicDid]


class AllowedSchemaList(BaseModel):
    """Represents a paginated list of allowed schemas.

    Attributes:
        page_size (int): The number of items per page.
        page_num (int): The current page number.
        count (int): The number of items in the current page.
        total_count (int): The total number of items across all pages.
        schemas (list[AllowedSchema]): The list of allowed schemas.
    """

    page_size: int
    page_num: int
    count: int
    total_count: int
    schemas: list[AllowedSchema]


class AllowedCredentialDefinitionList(BaseModel):
    """Represents a paginated list of allowed credential definitions.

    Attributes:
        page_size (int): The number of items per page.
        page_num (int): The current page number.
        count (int): The number of items in the current page.
        total_count (int): The total number of items across all pages.
        credentials (list[AllowedCredentialDefinition]):
            The list of allowed credential definitions.
    """

    page_size: int
    page_num: int
    count: int
    total_count: int
    credentials: list[AllowedCredentialDefinition]


class AllowedLogEntryList(BaseModel):
    """Represents a paginated list of allowed log entries.

    Attributes:
        page_size (int): The number of items per page.
        page_num (int): The current page number.
        count (int): The number of items in the current page.
        total_count (int): The total number of items across all pages.
        log_entries (list[AllowedLogEntry]): The list of allowed log entries.
    """

    page_size: int
    page_num: int
    count: int
    total_count: int
    log_entries: list[AllowedLogEntry]
