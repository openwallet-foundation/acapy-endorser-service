from enum import Enum
import logging
import os

from pydantic import BaseModel

from api.db.models.configuration import ConfigurationDB


logger = logging.getLogger(__name__)


class ConfigurationType(str, Enum):
    ENDORSER_AUTO_ACCEPT_CONNECTIONS = "ENDORSER_AUTO_ACCEPT_CONNECTIONS"
    ENDORSER_AUTO_ACCEPT_AUTHORS = "ENDORSER_AUTO_ACCEPT_AUTHORS"
    ENDORSER_AUTO_ENDORSE_REQUESTS = "ENDORSER_AUTO_ENDORSE_REQUESTS"
    ENDORSER_AUTO_ENDORSE_TXN_TYPES = "ENDORSER_AUTO_ENDORSE_TXN_TYPES"


class ConfigurationSource(str, Enum):
    Database = "Database"
    Environment = "Environment"
    Wallet = "Wallet"


class Configuration(BaseModel):
    config_id: str | None = None
    config_name: ConfigurationType
    config_value: str
    config_source: ConfigurationSource

    def json(self) -> dict:
        return {
            "config_name": self.config_name.name,
            "config_value": self.config_value,
            "config_source": self.config_source.name,
        }


CONFIG_DEFAULTS = {
    "ENDORSER_AUTO_ACCEPT_CONNECTIONS": "false",
    "ENDORSER_AUTO_ACCEPT_AUTHORS": "false",
    "ENDORSER_AUTO_ENDORSE_REQUESTS": "false",
    "ENDORSER_AUTO_ENDORSE_TXN_TYPES": "1,100,101,102,113,114",
}


def config_to_db_object(configuration: Configuration) -> ConfigurationDB:
    """Convert from model object to database model object."""
    logger.debug(f">>> from configuration: {configuration}")
    configdb: ConfigurationDB = ConfigurationDB(
        config_id=configuration.config_id,
        config_name=configuration.config_name.name,
        config_value=configuration.config_value,
    )
    logger.debug(f">>> to configdb: {configdb}")
    return configdb


def db_to_config_object(configdb: ConfigurationDB) -> Configuration:
    """Convert from database and env objects to model object."""
    configuration: Configuration = Configuration(
        config_id=str(configdb.config_id),
        config_name=ConfigurationType[configdb.config_name],
        config_value=configdb.config_value,
        config_source=ConfigurationSource.Database,
    )
    return configuration
