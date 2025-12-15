import os

import pytest
from api.db.errors import DoesNotExist
from api.db.models.configuration import ConfigurationDB
from api.endpoints.models.configurations import (
    Configuration,
    ConfigurationSource,
    ConfigurationType,
)
from api.services import configurations as svc


@pytest.mark.asyncio
async def test_get_config_record_from_db(monkeypatch):
    db_config = ConfigurationDB(
        config_id=None,
        config_name=ConfigurationType.ENDORSER_AUTO_ACCEPT_CONNECTIONS.name,
        config_value="true",
    )

    async def fake_fetch(db, name):
        return db_config

    monkeypatch.setattr(svc, "db_fetch_db_config_record", fake_fetch)

    cfg = await svc.get_config_record(
        db=None, config_name="ENDORSER_AUTO_ACCEPT_CONNECTIONS"
    )
    assert cfg.config_name is ConfigurationType.ENDORSER_AUTO_ACCEPT_CONNECTIONS
    assert cfg.config_value == "true"
    assert cfg.config_source is ConfigurationSource.Database


@pytest.mark.asyncio
async def test_get_config_record_env_fallback(monkeypatch):
    env_key = "ENDORSER_REJECT_BY_DEFAULT"
    os.environ[env_key] = "true"

    async def fake_fetch(db, name):
        raise DoesNotExist("missing")

    monkeypatch.setattr(svc, "db_fetch_db_config_record", fake_fetch)

    cfg = await svc.get_config_record(db=None, config_name=env_key)
    assert cfg.config_name is ConfigurationType.ENDORSER_REJECT_BY_DEFAULT
    assert cfg.config_value == "true"
    assert cfg.config_source is ConfigurationSource.Environment

    os.environ.pop(env_key, None)


@pytest.mark.asyncio
async def test_get_bool_config_truthy(monkeypatch):
    async def fake_get_config_record(db, name):
        return Configuration(
            config_id=None,
            config_name=ConfigurationType.ENDORSER_AUTO_ENDORSE_REQUESTS,
            config_value="YeS",
            config_source=ConfigurationSource.Database,
        )

    monkeypatch.setattr(svc, "get_config_record", fake_get_config_record)

    assert (
        await svc.get_bool_config(db=None, config_name="ENDORSER_AUTO_ENDORSE_REQUESTS")
        is True
    )


@pytest.mark.asyncio
async def test_get_bool_config_falsey(monkeypatch):
    async def fake_get_config_record(db, name):
        return Configuration(
            config_id=None,
            config_name=ConfigurationType.ENDORSER_AUTO_ENDORSE_REQUESTS,
            config_value="no",
            config_source=ConfigurationSource.Database,
        )

    monkeypatch.setattr(svc, "get_config_record", fake_get_config_record)

    assert (
        await svc.get_bool_config(db=None, config_name="ENDORSER_AUTO_ENDORSE_REQUESTS")
        is False
    )


@pytest.mark.asyncio
async def test_update_config_record_roundtrip(monkeypatch):
    # Validate that db_update_db_config_record is called with the payload from config_to_db_object
    captured = {}

    async def fake_get_config_record(db, name):
        return Configuration(
            config_id=None,
            config_name=ConfigurationType.ENDORSER_AUTO_ACCEPT_AUTHORS,
            config_value="false",
            config_source=ConfigurationSource.Database,
        )

    async def fake_db_update(db, db_config):
        captured["db_config"] = db_config
        # mimic writing and returning record with id set
        return ConfigurationDB(
            config_id="123",
            config_name=db_config.config_name,
            config_value=db_config.config_value,
        )

    monkeypatch.setattr(svc, "get_config_record", fake_get_config_record)
    monkeypatch.setattr(svc, "db_update_db_config_record", fake_db_update)

    updated = await svc.update_config_record(
        db=None, config_name="ENDORSER_AUTO_ACCEPT_AUTHORS", config_value="true"
    )

    assert captured["db_config"].config_value == "true"
    assert updated.config_id == "123"
    assert updated.config_value == "true"
    assert updated.config_name is ConfigurationType.ENDORSER_AUTO_ACCEPT_AUTHORS
