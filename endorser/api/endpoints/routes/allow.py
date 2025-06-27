"""Handle endpoints and DB ops for auto-endorsing DIDs, schemas, and cred definitions.

This module defines FastAPI endpoints that allow interaction with
authorization lists stored in the database. It provides CRUD
operations for DIDs, schemas, and credential definitions to define
which entities should be automatically endorsed when sent to the
ledger. It supports bulk updates via CSV upload, allowing both
appending to and replacing existing configurations.

Usage:
- Add, delete, and retrieve lists of DIDs, schemas, and credential definitions.
- Upload CSV files to manage authorization lists in bulk.

"""

from codecs import iterdecode
import logging
from csv import DictReader
from typing import Annotated, Optional, TypeVar
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.functions import func
from starlette import status
from starlette.status import HTTP_409_CONFLICT, HTTP_500_INTERNAL_SERVER_ERROR

from api.db.errors import AlreadyExists
from api.db.models.allow import (
    AllowedCredentialDefinition,
    AllowedSchema,
)
from api.db.models.base import BaseModel
from api.endpoints.dependencies.db import get_db
from api.endpoints.models.allow import (
    AllowedCredentialDefinitionList,
    AllowedPublicDid,
    AllowedPublicDidList,
    AllowedSchemaList,
)
from api.services.allow_lists import add_to_allow_list, updated_allowed

router = APIRouter()
logger = logging.getLogger(__name__)


def db_to_http_exception(e: Exception) -> int:
    """Convert database exceptions to HTTP status codes."""
    match e:
        case IntegrityError():
            return HTTP_409_CONFLICT
        case AlreadyExists():
            return HTTP_409_CONFLICT
        case _:
            return HTTP_500_INTERNAL_SERVER_ERROR


T = TypeVar("T", bound=BaseModel)
J = TypeVar("J")


async def select_from_table(
    db: AsyncSession,
    filters: dict[J | None, J],
    table: type[T],
    page_num: int,
    page_size: int,
) -> tuple[int, list[T]]:
    """Select and filter data from a table asynchronously."""
    skip = (page_num - 1) * page_size
    filter_conditions = [
        cond == value if value else True for value, cond in filters.items()
    ]
    base_q = select(table).filter(*filter_conditions)
    count_q = base_q.with_only_columns(func.count()).order_by(None)
    q = base_q.limit(page_size).offset(skip)
    count_result = await db.execute(count_q)
    total_count: int = count_result.scalar() or 0

    result = await db.execute(q)
    db_txn: list[T] = result.scalars().all()
    return (total_count, db_txn)


@router.get(
    "/publish-did",
    status_code=status.HTTP_200_OK,
    response_model=AllowedPublicDidList,
    description="Get a list of DIDs that will be auto endorsed\
    when sent to the ledger by an author",
)
async def get_allowed_dids(
    did: Optional[str] = None,
    page_size: int = 10,
    page_num: int = 1,
    db: AsyncSession = Depends(get_db),
) -> AllowedPublicDidList:
    """Fetch allowed public DIDs with pagination."""
    try:
        total_count: int
        db_txn: list[AllowedPublicDid]
        total_count, db_txn = await select_from_table(
            db,
            {did: AllowedPublicDid.registered_did},
            AllowedPublicDid,
            page_num,
            page_size,
        )

        return AllowedPublicDidList(
            page_size=page_size,
            page_num=page_num,
            total_count=total_count,
            count=len(db_txn),
            dids=db_txn,
        )
    except Exception as e:
        raise HTTPException(status_code=db_to_http_exception(e), detail=str(e))


@router.post(
    "/publish-did/{did}",
    status_code=status.HTTP_200_OK,
    response_model=AllowedPublicDid,
    description="Add a new DID that will be auto endorsed when published by an author.\
    Any field marked with a * or left empty match on any value.",
)
async def add_allowed_did(
    did: str = "*",
    details: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> AllowedPublicDid:
    """Add a new DID to the allow list."""
    try:
        adid = AllowedPublicDid(registered_did=did, details=details)
        return await add_to_allow_list(db, adid)
    except Exception as e:
        raise HTTPException(status_code=db_to_http_exception(e), detail=str(e))


@router.delete(
    "/publish-did/{did}",
    status_code=status.HTTP_200_OK,
    response_model=dict,
    description="Remove a DID from the list of DIDs that will be auto endorsed\
    when published to the ledger",
)
async def delete_allowed_did(
    did: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Delete a DID from the allow list."""
    try:
        q = delete(AllowedPublicDid).where(AllowedPublicDid.registered_did == did)
        await db.execute(q)
        await updated_allowed(db)
        return {}
    except Exception as e:
        raise HTTPException(status_code=db_to_http_exception(e), detail=str(e))


@router.get(
    "/schema",
    status_code=status.HTTP_200_OK,
    response_model=AllowedSchemaList,
    description="Get a list of schemas that will be auto endorsed\
    when sent to the ledger by an author",
)
async def get_allowed_schemas(
    allowed_schema_id: Optional[UUID] = None,
    author_did: Optional[str] = None,
    schema_name: Optional[str] = None,
    version: Optional[str] = None,
    page_size: int = 10,
    page_num: int = 1,
    db: AsyncSession = Depends(get_db),
) -> AllowedSchemaList:
    """Fetch allowed schemas with pagination."""
    try:
        filter = {
            allowed_schema_id: AllowedSchema.allowed_schema_id,
            author_did: AllowedSchema.author_did,
            schema_name: AllowedSchema.schema_name,
            version: AllowedSchema.version,
        }

        db_txn: list[AllowedSchema]
        total_count, db_txn = await select_from_table(
            db, filter, AllowedSchema, page_num, page_size
        )
        return AllowedSchemaList(
            page_size=page_size,
            page_num=page_num,
            total_count=total_count,
            count=len(db_txn),
            schemas=db_txn,
        )
    except Exception as e:
        raise HTTPException(status_code=db_to_http_exception(e), detail=str(e))


@router.post(
    "/schema",
    status_code=status.HTTP_200_OK,
    response_model=AllowedSchema,
    description="Add a new schema that will be auto endorsed\
    when sent to the ledger by an author.\
    Any field marked with a * or left empty match on any value.",
)
async def add_allowed_schema(
    author_did: str = "*",
    schema_name: str = "*",
    version: str = "*",
    details: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> AllowedSchema:
    """Add a new schema to the allow list."""
    try:
        tmp = AllowedSchema(
            author_did=author_did,
            schema_name=schema_name,
            version=version,
            details=details,
        )
        return await add_to_allow_list(db, tmp)
    except Exception as e:
        raise HTTPException(status_code=db_to_http_exception(e), detail=str(e))


@router.delete(
    "/schema",
    status_code=status.HTTP_200_OK,
    response_model=dict,
    description="Remove a schema from the list of schemas that will be auto endorsed\
    when sent to the ledger",
)
async def delete_allowed_schema(
    allowed_schema_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Delete a schema from the allow list."""
    try:
        q = delete(AllowedSchema).where(
            AllowedSchema.allowed_schema_id == allowed_schema_id
        )
        await db.execute(q)
        await updated_allowed(db)
        return {}
    except Exception as e:
        raise HTTPException(status_code=db_to_http_exception(e), detail=str(e))


@router.get(
    "/credential-definition",
    status_code=status.HTTP_200_OK,
    response_model=AllowedCredentialDefinitionList,
    description="Get a list of credential definitions that will be auto endorsed\
    when sent to the ledger by an author",
)
async def get_allowed_cred_def(
    allowed_cred_def_id: Optional[UUID] = None,
    schema_issuer_did: Optional[str] = None,
    creddef_author_did: Optional[str] = None,
    schema_name: Optional[str] = None,
    version: Optional[str] = None,
    tag: Optional[str] = None,
    rev_reg_def: Optional[bool] = None,
    rev_reg_entry: Optional[bool] = None,
    page_size: int = 10,
    page_num: int = 1,
    db: AsyncSession = Depends(get_db),
) -> AllowedCredentialDefinitionList:
    """Fetch allowed credential definitions with pagination."""
    try:
        filters = {
            allowed_cred_def_id: AllowedCredentialDefinition.allowed_cred_def_id,
            schema_issuer_did: AllowedCredentialDefinition.schema_issuer_did,
            creddef_author_did: AllowedCredentialDefinition.creddef_author_did,
            schema_name: AllowedCredentialDefinition.schema_name,
            version: AllowedCredentialDefinition.version,
            tag: AllowedCredentialDefinition.tag,
            rev_reg_def: AllowedCredentialDefinition.rev_reg_def,
            rev_reg_entry: AllowedCredentialDefinition.rev_reg_entry,
        }

        db_txn: list[AllowedCredentialDefinition]
        total_count, db_txn = await select_from_table(
            db, filters, AllowedCredentialDefinition, page_num, page_size
        )
        await updated_allowed(db)
        return AllowedCredentialDefinitionList(
            page_size=page_size,
            page_num=page_num,
            total_count=total_count,
            count=len(db_txn),
            credentials=db_txn,
        )
    except Exception as e:
        raise HTTPException(status_code=db_to_http_exception(e), detail=str(e))


@router.post(
    "/credential-definition",
    status_code=status.HTTP_200_OK,
    response_model=AllowedCredentialDefinition,
    description="Add a new credential definition that will be auto endorsed when\
    sent to the ledger by an author.\
    Any field marked with a * or left empty match on any value.",
)
async def add_allowed_cred_def(
    schema_issuer_did: str = "*",
    creddef_author_did: str = "*",
    schema_name: str = "*",
    version: str = "*",
    tag: str = "*",
    details: str | None = None,
    rev_reg_def: bool = True,
    rev_reg_entry: bool = True,
    db: AsyncSession = Depends(get_db),
) -> AllowedCredentialDefinition:
    """Add a new credential definition to the allow list."""
    try:
        acreddef = AllowedCredentialDefinition(
            schema_issuer_did=schema_issuer_did,
            creddef_author_did=creddef_author_did,
            schema_name=schema_name,
            tag=tag,
            rev_reg_def=rev_reg_def,
            rev_reg_entry=rev_reg_entry,
            version=version,
            details=details,
        )
        return await add_to_allow_list(db, acreddef)
    except Exception as e:
        raise HTTPException(status_code=db_to_http_exception(e), detail=str(e))


@router.delete(
    "/credential-definition",
    status_code=status.HTTP_200_OK,
    response_model=dict,
    description="Remove a credential definition from the list of credential \
    definitions that will be auto endorsed when sent to the ledger",
)
async def delete_allowed_cred_def(
    allowed_cred_def_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Delete a credential definition from the allow list."""
    try:
        q = delete(AllowedCredentialDefinition).where(
            AllowedCredentialDefinition.allowed_cred_def_id == allowed_cred_def_id
        )
        await db.execute(q)
        await updated_allowed(db)
        return {}
    except Exception as e:
        raise HTTPException(status_code=db_to_http_exception(e), detail=str(e))


def maybe_str_to_bool(s: str) -> str | bool:
    """Convert string to boolean if applicable."""
    return s == "True" if isinstance(s, str) else s


def construct_allowed_credential_definition(cd: dict) -> AllowedCredentialDefinition:
    """Construct AllowedCredentialDefinition with proper boolean conversion."""
    cd["rev_reg_def"] = maybe_str_to_bool(cd["rev_reg_def"])
    cd["rev_reg_entry"] = maybe_str_to_bool(cd["rev_reg_entry"])
    ncd = AllowedCredentialDefinition(**cd)
    return ncd


async def update_allowed_config(k, v, db):
    """Update the allowed configuration in the database with entries from a CSV file.

    This function reads a CSV file, constructs instances of specified classes,
    and adds them to the database.

    Args:
        k: An object with attributes 'file' (CSV file handle)
           and 'filename' (name of the CSV file).
        v: A class type, used to construct instances from CSV data.
        db: Database session to which the constructed instances are added.

    Returns:
        A dictionary containing the filename and list of constructed class instances.

    """
    csvReader = DictReader(iterdecode(k.file, "utf-8"))
    constructed_classes = [
        (
            construct_allowed_credential_definition(i)
            if v is AllowedCredentialDefinition
            else v(**i)
        )
        for i in csvReader
    ]
    tmp = {
        "file_name": k.filename,
        "contents": constructed_classes,
    }
    for i in tmp["contents"]:
        db.add(i)
    return tmp


async def update_full_config(
    publish_did: Optional[UploadFile],
    schema: Optional[UploadFile],
    credential_definition: Optional[UploadFile],
    db: AsyncSession,
    delete_contents: bool,
) -> dict:
    """Update full configuration, possibly deleting existing entries."""
    correlated_tables = {
        publish_did: AllowedPublicDid,
        schema: AllowedSchema,
        credential_definition: AllowedCredentialDefinition,
    }
    modifications = {}
    for k, v in correlated_tables.items():
        if k:
            if delete_contents:
                await db.execute(delete(v))
            modifications[v.__name__] = await update_allowed_config(k, v, db)
    await db.commit()
    await updated_allowed(db)
    return modifications


@router.post(
    "/config",
    status_code=status.HTTP_200_OK,
    response_model=dict,
    description="Upload a new CSV config replacing the existing configuration.",
)
async def set_config(
    publish_did: Annotated[
        UploadFile, File(description="List of DIDs authorized to become public")
    ] = None,
    schema: Annotated[
        UploadFile, File(description="List of schemas authorized to be published")
    ] = None,
    credential_definition: Annotated[
        UploadFile, File(description="List of creddefs authorized to be published")
    ] = None,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Set new configuration by uploading CSVs, replacing the existing configuration."""
    try:
        return await update_full_config(
            publish_did, schema, credential_definition, db, True
        )
    except Exception as e:
        raise HTTPException(status_code=db_to_http_exception(e), detail=str(e))


@router.put(
    "/config",
    status_code=status.HTTP_200_OK,
    response_model=dict,
    description="Upload a new CSV config appending to the existing configuration.",
)
async def append_config(
    publish_did: Annotated[
        UploadFile, File(description="List of DIDs authorized to become public")
    ] = None,
    schema: Annotated[
        UploadFile, File(description="List of schemas authorized to be published")
    ] = None,
    credential_definition: Annotated[
        UploadFile, File(description="List of authorized creddefs")
    ] = None,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Append new configuration by uploading CSVs to the existing configuration."""
    try:
        return await update_full_config(
            publish_did, schema, credential_definition, db, False
        )
    except Exception as e:
        raise HTTPException(status_code=db_to_http_exception(e), detail=str(e))
