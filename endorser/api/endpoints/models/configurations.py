"""Configuration management for the Aries Endorser Service.

This module handles the configuration settings for the Aries Endorser
Service, providing classes and methods to manage configurations from
different sources, such as environment variables, databases, and
wallets. It includes conversion functions to translate between model
objects and database representations.

"""

from enum import Enum
import logging

from pydantic import BaseModel

from api.db.models.configuration import ConfigurationDB


logger = logging.getLogger(__name__)


class ConfigurationType(str, Enum):
    """Enum for different types of configuration settings."""

    ENDORSER_AUTO_ACCEPT_CONNECTIONS = "ENDORSER_AUTO_ACCEPT_CONNECTIONS"
    ENDORSER_AUTO_ACCEPT_AUTHORS = "ENDORSER_AUTO_ACCEPT_AUTHORS"
    ENDORSER_AUTO_ENDORSE_REQUESTS = "ENDORSER_AUTO_ENDORSE_REQUESTS"
    ENDORSER_AUTO_ENDORSE_TXN_TYPES = "ENDORSER_AUTO_ENDORSE_TXN_TYPES"
    ENDORSER_REJECT_BY_DEFAULT = "ENDORSER_REJECT_BY_DEFAULT"


class ConfigurationSource(str, Enum):
    """Enum for different configuration sources."""

    Database = "Database"
    Environment = "Environment"
    Wallet = "Wallet"


class Configuration(BaseModel):
    """Model for storing configuration settings."""

    config_id: str | None = None
    config_name: ConfigurationType
    config_value: str
    config_source: ConfigurationSource

    def json(self) -> dict:
        """Converts the configuration to a JSON-compatible dictionary."""
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
    "ENDORSER_REJECT_BY_DEFAULT": "false",
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
