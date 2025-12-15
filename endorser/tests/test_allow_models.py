import uuid

from api.db.models.allow import (
    AllowedLogEntry,
    allowed_cred_def_uuid,
    allowed_log_entry_uuid,
    allowed_schema_uuid,
)


class DummyContext:
    def __init__(self, params: dict):
        self._params = params

    def get_current_parameters(self):
        return self._params


def test_allowed_schema_uuid_deterministic():
    params = {
        "author_did": "did:example:author",
        "schema_name": "degree",
        "version": "1.0",
    }
    ctx = DummyContext(params)
    expected = uuid.uuid5(
        uuid.NAMESPACE_OID,
        params["author_did"] + params["schema_name"] + params["version"],
    )
    assert allowed_schema_uuid(ctx) == expected


def test_allowed_log_entry_uuid_deterministic():
    params = {
        "domain": "example.com",
        "namespace": "ns",
        "identifier": "id-1",
    }
    ctx = DummyContext(params)
    expected = uuid.uuid5(
        uuid.NAMESPACE_OID,
        params["domain"] + params["namespace"] + params["identifier"],
    )
    assert allowed_log_entry_uuid(ctx) == expected


def test_allowed_cred_def_uuid_deterministic():
    params = {
        "schema_issuer_did": "did:issuer",
        "creddef_author_did": "did:author",
        "schema_name": "degree",
        "version": "1.0",
        "tag": "tag1",
    }
    ctx = DummyContext(params)
    expected = uuid.uuid5(
        uuid.NAMESPACE_OID,
        params["schema_issuer_did"]
        + params["creddef_author_did"]
        + params["schema_name"]
        + params["version"]
        + params["tag"],
    )
    assert allowed_cred_def_uuid(ctx) == expected


def test_allowed_log_entry_default_log_updates_false():
    entry = AllowedLogEntry(
        scid="scid", domain="d", namespace="n", identifier="id", version="1"
    )
    assert entry.log_updates is False
