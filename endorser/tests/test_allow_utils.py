from io import BytesIO

import pytest
from api.db.errors import AlreadyExists
from api.db.models.allow import AllowedCredentialDefinition, AllowedLogEntry
from api.endpoints.routes.allow import (
    construct_allowed_credential_definition,
    db_to_http_exception,
    maybe_str_to_bool,
    update_allowed_config,
)
from sqlalchemy.exc import IntegrityError
from starlette import status


class DummySession:
    """Minimal async session stub capturing added objects."""

    def __init__(self) -> None:
        self.added: list[object] = []

    def add(self, obj: object) -> None:
        self.added.append(obj)


class DummyUploadFile:
    """UploadFile-like stub for feeding CSV content to update_allowed_config."""

    def __init__(self, filename: str, content: bytes) -> None:
        self.filename = filename
        self.file = BytesIO(content)


def test_db_to_http_exception_mappings():
    dummy_err = IntegrityError(statement="", params="", orig=Exception())
    assert db_to_http_exception(dummy_err) == status.HTTP_409_CONFLICT
    assert db_to_http_exception(AlreadyExists()) == status.HTTP_409_CONFLICT
    assert db_to_http_exception(RuntimeError()) == status.HTTP_500_INTERNAL_SERVER_ERROR


def test_maybe_str_to_bool_conversions():
    assert maybe_str_to_bool("True") is True
    assert maybe_str_to_bool("False") is False
    assert maybe_str_to_bool(True) is True
    assert maybe_str_to_bool(False) is False
    assert maybe_str_to_bool("anything-else") is False


def test_construct_allowed_credential_definition_bool_conversion():
    data = {
        "schema_issuer_did": "did:peer:issuer",
        "creddef_author_did": "did:peer:author",
        "schema_name": "degree",
        "version": "1.0",
        "tag": "tag1",
        "rev_reg_def": "True",
        "rev_reg_entry": "False",
        "details": None,
    }
    model = construct_allowed_credential_definition(data)
    assert isinstance(model, AllowedCredentialDefinition)
    assert model.rev_reg_def is True
    assert model.rev_reg_entry is False


@pytest.mark.asyncio
async def test_update_allowed_config_reads_csv_and_adds_models():
    csv_content = (
        "scid,domain,namespace,identifier,version,log_updates\n"
        "scid-1,example.com,ns,id-1,1,true\n"
        "scid-2,example.com,ns,id-2,2,false\n"
    ).encode()
    upload = DummyUploadFile("log_entries.csv", csv_content)
    db = DummySession()

    result = await update_allowed_config(upload, AllowedLogEntry, db)

    assert result["file_name"] == "log_entries.csv"
    assert len(result["contents"]) == 2
    assert all(isinstance(item, AllowedLogEntry) for item in result["contents"])
    # ensure objects were added to the session stub
    assert db.added == result["contents"]


@pytest.mark.asyncio
async def test_update_allowed_config_handles_creddef_bool_strings():
    csv_content = (
        "schema_issuer_did,creddef_author_did,schema_name,version,tag,rev_reg_def,rev_reg_entry,details\n"
        "issuer,author,degree,1.0,tag1,True,False,info\n"
    ).encode()
    upload = DummyUploadFile("cred_defs.csv", csv_content)
    db = DummySession()

    result = await update_allowed_config(upload, AllowedCredentialDefinition, db)

    model = result["contents"][0]
    assert model.rev_reg_def is True
    assert model.rev_reg_entry is False
    assert db.added == result["contents"]
