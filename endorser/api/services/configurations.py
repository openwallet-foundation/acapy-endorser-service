"""This module manages configuration records in the database for the Endorser service.

It provides functions to create, read, update, and retrieve configuration settings,
handling defaults and environment variables as necessary.

Functions:
- db_add_db_config_record: Add a new configuration record to the database.
- db_fetch_db_config_record: Fetch a specific configuration record by name.
- db_update_db_config_record: Update an existing configuration record.
- db_get_config_records: Retrieve all configuration records from the database.
- get_config_record: Get a specific configuration record, falling back to defaults.
- get_config_records: Get all configuration records as Configuration objects.
- update_config_record: Update a configuration record's value and return the new state.
- get_bool_config: Retrieve a configuration as a boolean value.
- get_config: Retrieve a configuration value as a string.
"""

import logging
import os

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.errors import DoesNotExist
from api.db.models.configuration import ConfigurationDB
from api.endpoints.models.configurations import (
    CONFIG_DEFAULTS,
    Configuration,
    ConfigurationSource,
    ConfigurationType,
    config_to_db_object,
    db_to_config_object,
)

logger = logging.getLogger(__name__)

TRUE_VALUES = ["true", "1", "t", "y", "yes", "yeah", "yup", "certainly", "uh-huh"]


async def db_add_db_config_record(db: AsyncSession, db_config: ConfigurationDB):
    """Add a configuration record to the database."""
    logger.debug(f">>> adding config: {db_config} ...")
    db.add(db_config)
    await db.commit()


async def db_fetch_db_config_record(
    db: AsyncSession, config_name: str
) -> ConfigurationDB:
    """Fetch a configuration record from the database by its name."""
    logger.info(f">>> db_fetch_db_config_record() for {config_name}")
    q = select(ConfigurationDB).where(ConfigurationDB.config_name == config_name)
    result = await db.execute(q)
    result_rec = result.scalar_one_or_none()
    if not result_rec:
        raise DoesNotExist(
            f"{ConfigurationDB.__name__}<config_name:{config_name}> does not exist"
        )
    return result_rec


async def db_update_db_config_record(
    db: AsyncSession, db_config: ConfigurationDB
) -> ConfigurationDB:
    """Update an existing configuration record in the database or add a new one.

    Args:
        db (AsyncSession): The database session to use.
        db_config (ConfigurationDB): The configuration to update or add.

    Returns:
        ConfigurationDB: The updated or newly added configuration record.
    """
    if db_config.config_id is None:
        await db_add_db_config_record(db, db_config)
    else:
        logger.debug(f">>> updating config: {db_config} ...")
        payload_dict = db_config.dict()
        q = (
            update(ConfigurationDB)
            .where(ConfigurationDB.config_id == db_config.config_id)
            .where(ConfigurationDB.config_name == db_config.config_name)
            .values(payload_dict)
        )
        await db.execute(q)
        await db.commit()
    return await db_fetch_db_config_record(db, db_config.config_name)


async def db_get_config_records(db: AsyncSession) -> list[ConfigurationDB]:
    """Retrieve all configuration records from the database."""
    filters = []

    # build out a base query with all filters
    base_q = select(ConfigurationDB).filter(*filters)
    results_q_recs = await db.execute(base_q)
    db_configs = results_q_recs.scalars().all()

    return db_configs


async def get_config_record(db: AsyncSession, config_name: str) -> Configuration:
    """Retrieve a configuration record from the database or return a default.

    Args:
        db (AsyncSession): The database session.
        config_name (str): The name of the configuration.

    Returns:
        Configuration: The configuration object with the config value and source.
    """
    try:
        db_config = await db_fetch_db_config_record(db, config_name)
        config = db_to_config_object(db_config)
        return config
    except DoesNotExist:
        default = (
            CONFIG_DEFAULTS[config_name]
            if config_name in CONFIG_DEFAULTS[config_name]
            else ""
        )
        config: Configuration = Configuration(
            config_id=None,
            config_name=ConfigurationType[config_name],
            config_value=os.getenv(config_name, default),
            config_source=ConfigurationSource.Environment,
        )
        return config


async def get_config_records(db: AsyncSession) -> list[Configuration]:
    """Fetch configuration records for all configuration types."""
    config_list = []
    for config_type in ConfigurationType:
        config = await get_config_record(db, config_type.name)
        config_list.append(config)
    return config_list


async def update_config_record(
    db: AsyncSession,
    config_name: str,
    config_value: str,
) -> Configuration:
    """Update the configuration record with a new value."""
    old_config = await get_config_record(db, config_name)
    old_config.config_value = config_value
    old_db_config = config_to_db_object(old_config)
    new_db_config = await db_update_db_config_record(db, old_db_config)
    new_config = db_to_config_object(new_db_config)
    return new_config


async def get_bool_config(db: AsyncSession, config_name: str) -> bool:
    """Retrieve a boolean configuration value from the database."""

    config = await get_config_record(db, config_name)
    config_bool = config.config_value.lower() in TRUE_VALUES
    logger.debug(
        f"get_bool_config({config_name}) -> {config.config_value} = {config_bool}"
    )
    return config_bool


async def get_config(db: AsyncSession, config_name: str) -> str:
    """Retrieve the configuration value for the given config name."""
    config = await get_config_record(db, config_name)
    config_val = config.config_value
    return config_val
