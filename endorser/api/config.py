"""This module defines configuration settings for the Aries Endorser Service.

The module provides an enum for environment modes, functions to handle configuration
values, and a global configuration class that supports both local and production
environments. It allows for easy retrieval and setup of environment-specific settings
through `GlobalConfig`, `LocalConfig`, and `ProdConfig` classes. The configurations
are set using environment variables, and the settings are cached for performance.
The get_configuration function fetches and returns the appropriate configuration
based on the "ENVIRONMENT" environment variable, establishing the service's runtime
parameters.

Classes:
- EnvironmentEnum: Enumeration representing different environment modes.
- GlobalConfig: Base class defining configuration attributes for the service.
- LocalConfig: Configuration subclass for the local environment.
- ProdConfig: Configuration subclass for the production environment.
- FactoryConfig: Initializes the appropriate configuration based on the environment.

Functions:
- to_bool: Utility to convert truthy strings to boolean values.
- get_configuration: Retrieves the cached global configuration for
                     the current environment.
"""

import logging
import os
from enum import Enum
from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


logger = logging.getLogger(__name__)


class EnvironmentEnum(str, Enum):
    """Enumeration representing different environment modes.

    Attributes:
        PRODUCTION: Represents the production environment.
        LOCAL: Represents the local environment.
    """

    PRODUCTION = "production"
    LOCAL = "local"


def to_bool(s: str) -> bool:
    """Convert a string representation of truth to a boolean.

    Args:
        s (str): The string to evaluate.

    Returns:
        bool: True if the string represents a true value, otherwise False.

    The function is case-insensitive and recognizes the following as true values:
    "true", "1", "t", "y", "yes", "yeah", "yup", "certainly", "uh-huh".
    """
    return s.lower() in [
        "true",
        "1",
        "t",
        "y",
        "yes",
        "yeah",
        "yup",
        "certainly",
        "uh-huh",
    ]


class GlobalConfig(BaseSettings):
    """Configuration class for the Endorser Service.

    Attributes:
        TITLE (str): The public name of the endorser service.
        DESCRIPTION (str): Brief description of the service.
        ENVIRONMENT (EnvironmentEnum): Current environment setting.
        DEBUG (bool): Flag for enabling debug mode.
        TESTING (bool): Flag for enabling testing mode.
        TIMEZONE (str): The timezone setting, default is "UTC".
        ENDORSER_AUTO_ACCEPT_CONNECTIONS (bool): Flag to auto-accept connections.
        ENDORSER_AUTO_ACCEPT_AUTHORS (bool): Flag to auto-accept authors.
        ENDORSER_AUTO_ENDORSE_REQUESTS (bool): Flag to auto-endorse requests.
        ENDORSER_AUTO_ENDORSE_TXN_TYPES (str): Types of transactions to auto-endorse.
        ENDORSER_REJECT_BY_DEFAULT (bool): Flag to auto-reject transactions by default.
        PSQL_HOST (str): Host for PostgreSQL connection.
        PSQL_PORT (int): Port for PostgreSQL connection.
        PSQL_DB (str): Database name for the endorser.
        PSQL_USER (str): User for the PostgreSQL connection.
        PSQL_PASS (str): Password for the PostgreSQL connection.
        PSQL_ADMIN_USER (str): Admin user for PostgreSQL migrations.
        PSQL_ADMIN_PASS (str): Admin password for PostgreSQL migrations.
        SQLALCHEMY_DATABASE_URI (str): SQLAlchemy database URI for async connections.
        SQLALCHEMY_DATABASE_ADMIN_URI (str): SQLAlchemy database URI for sync
                                             admin connections.
        ACAPY_ADMIN_URL (str): Admin URL for the Aries Cloud Agent.
        ACAPY_ADMIN_URL_API_KEY (str): API key for ACAPY admin access.
        ACAPY_WALLET_AUTH_TOKEN (str | None): Authentication token for ACAPY wallet.
        ENDORSER_API_ADMIN_USER (str): Username for the endorser API admin.
        ENDORSER_API_ADMIN_KEY (str): Key for the endorser API admin.
        ENDORSER_WEBHOOK_URL (str): Webhook URL for the endorser.
        ACAPY_WEBHOOK_URL_API_KEY_NAME (str): Header name for API key in webhook URL.
        ACAPY_WEBHOOK_URL_API_KEY (str): API key for the ACAPY webhook URL.
        DB_ECHO_LOG (bool): Flag to enable SQLAlchemy echo.
        API_V1_STR (str): API version 1 prefix.
        JWT_SECRET_KEY (str): Secret key for JWT encoding.
        JWT_ALGORITHM (str): Algorithm used for JWT.
        JWT_ACCESS_TOKEN_EXPIRE_MINUTES (int): Minutes before JWT access token expires.
        model_config (SettingsConfigDict): Configuration for settings model.
    """

    TITLE: str = os.environ.get("ENDORSER_PUBLIC_NAME", "Endorser")
    DESCRIPTION: str = os.environ.get(
        "ENDORSER_PUBLIC_DESC", "An endorser service for aca-py wallets"
    )

    ENVIRONMENT: EnvironmentEnum
    DEBUG: bool = False
    TESTING: bool = False
    TIMEZONE: str = "UTC"

    # configuration
    ENDORSER_AUTO_ACCEPT_CONNECTIONS: bool = to_bool(
        os.environ.get("ENDORSER_AUTO_ACCEPT_CONNECTIONS", "false")
    )
    ENDORSER_AUTO_ACCEPT_AUTHORS: bool = to_bool(
        os.environ.get("ENDORSER_AUTO_ACCEPT_AUTHORS", "false")
    )
    ENDORSER_AUTO_ENDORSE_REQUESTS: bool = to_bool(
        os.environ.get("ENDORSER_AUTO_ENDORSE_REQUESTS", "false")
    )
    ENDORSER_AUTO_ENDORSE_TXN_TYPES: str = os.environ.get(
        "ENDORSER_AUTO_ENDORSE_TXN_TYPES", ""
    )

    ENDORSER_REJECT_BY_DEFAULT: bool = to_bool(
        os.environ.get("ENDORSER_REJECT_BY_DEFAULT", "false")
    )

    # the following defaults match up with default values in scripts/.env.example
    # these MUST be all set in non-local environments.
    PSQL_HOST: str = os.environ.get("CONTROLLER_POSTGRESQL_HOST", "localhost")
    PSQL_PORT: int = os.environ.get("CONTROLLER__POSTGRESQL_PORT", 5432)
    PSQL_DB: str = os.environ.get("CONTROLLER_POSTGRESQL_DB", "endorser_controller_db")

    PSQL_USER: str = os.environ.get("CONTROLLER_POSTGRESQL_USER", "")
    PSQL_PASS: str = os.environ.get("CONTROLLER_POSTGRESQL_PASSWORD", "")

    PSQL_ADMIN_USER: str = os.environ.get("CONTROLLER_POSTGRESQL_ADMIN_USER", "")
    PSQL_ADMIN_PASS: str = os.environ.get("CONTROLLER_POSTGRESQL_ADMIN_PASSWORD", "")

    # application connection is async
    # fmt: off
    SQLALCHEMY_DATABASE_URI: str = (
        f"postgresql+asyncpg://{PSQL_USER}:{PSQL_PASS}@{PSQL_HOST}:{PSQL_PORT}/{PSQL_DB}"  # noqa: E501
    )
    # migrations connection uses owner role and is synchronous
    SQLALCHEMY_DATABASE_ADMIN_URI: str = (
        f"postgresql://{PSQL_ADMIN_USER}:{PSQL_ADMIN_PASS}@{PSQL_HOST}:{PSQL_PORT}/{PSQL_DB}"  # noqa: E501
    )
    # fmt: on

    ACAPY_ADMIN_URL: str = os.environ.get("ACAPY_ADMIN_URL", "http://localhost:9031")
    ACAPY_ADMIN_URL_API_KEY: str = os.environ.get("ACAPY_API_ADMIN_KEY", "change-me")
    ACAPY_WALLET_AUTH_TOKEN: str | None = os.environ.get("ACAPY_WALLET_AUTH_TOKEN")

    ENDORSER_API_ADMIN_USER: str = os.environ.get("ENDORSER_API_ADMIN_USER", "endorser")
    ENDORSER_API_ADMIN_KEY: str = os.environ.get("ENDORSER_API_ADMIN_KEY", "change-me")

    ENDORSER_WEBHOOK_URL: str = os.environ.get(
        "ENDORSER_WEBHOOK_URL", "http://aries-endorser-api:5000/webhook"
    )
    ACAPY_WEBHOOK_URL_API_KEY_NAME: str = "x-api-key"
    ACAPY_WEBHOOK_URL_API_KEY: str = os.environ.get("ACAPY_WEBHOOK_URL_API_KEY", "")

    DB_ECHO_LOG: bool = False

    # Api V1 prefix
    API_V1_STR: str = "/v1"

    # Generate a secure JWT secret key if not provided via environment
    JWT_SECRET_KEY: str = os.environ.get("JWT_SECRET_KEY", "change-me")
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 300
    model_config = SettingsConfigDict(case_sensitive=True)


class LocalConfig(GlobalConfig):
    """Local configurations."""

    DEBUG: bool = True
    DB_ECHO_LOG: bool = True
    ENVIRONMENT: EnvironmentEnum = EnvironmentEnum.LOCAL


class ProdConfig(GlobalConfig):
    """Production configurations."""

    DEBUG: bool = False
    ENVIRONMENT: EnvironmentEnum = EnvironmentEnum.PRODUCTION


class FactoryConfig:
    """FactoryConfig creates a configuration instance based on the specified environment.

    Initialize with an optional environment string to return a
    configuration for "local" or "production" environments.

    """

    def __init__(self, environment: Optional[str]):
        """Initialize a FactoryConfig instance with the given environment.

        :param environment: Optional; the environment type as a string.
        """
        self.environment = environment

    def __call__(self) -> GlobalConfig:
        """Return the appropriate configuration instance based on the environment.

        :return: LocalConfig instance if environment is 'LOCAL',
                 otherwise ProdConfig instance.
        """
        if self.environment == EnvironmentEnum.LOCAL.value:
            return LocalConfig()
        return ProdConfig()


@lru_cache()
def get_configuration() -> GlobalConfig:
    """Retrieve the global configuration based on the current environment setting.

    This function fetches the environment variable "ENVIRONMENT" to determine
    the appropriate configuration to use and returns an instance of GlobalConfig.

    Returns:
        GlobalConfig: An instance of the configuration for the specified environment.
    """
    return FactoryConfig(os.environ.get("ENVIRONMENT"))()


settings = get_configuration()
