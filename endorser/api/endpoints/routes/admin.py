"""APIRouter module for managing endorser configurations in an async FastAPI context."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from api.endpoints.dependencies.db import get_db
from api.endpoints.dependencies.jwt_security import check_access_token
from api.endpoints.models.configurations import ConfigurationType
from api.services.admin import (
    get_endorser_configs,
    get_endorser_config,
    validate_endorser_config,
    update_endorser_config,
)
from api.endpoints.models.configurations import (
    Configuration,
)
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR


logger = logging.getLogger(__name__)

router = APIRouter(tags=["admin"], dependencies=[Depends(check_access_token)])


@router.get("/config", status_code=status.HTTP_200_OK, response_model=dict)
async def get_config(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Retrieve endorser configurations with optional sorting and paging.

    Note: JWT token validation is handled at the router level.

    Args:
        db (AsyncSession): Database session dependency.

    Returns:
        dict: Endorser configurations.

    Raises:
        HTTPException: If an error occurs while retrieving configurations.
    """
    try:
        endorser_configs = await get_endorser_configs(db)
        return endorser_configs
    except Exception as e:
        raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get(
    "/config/{config_name}",
    status_code=status.HTTP_200_OK,
    response_model=Configuration,
)
async def get_config_by_name(
    config_name: str,
    db: AsyncSession = Depends(get_db),
) -> Configuration:
    """Retrieve an endorser configuration by name asynchronously."""
    # This should take some query params, sorting and paging params...
    try:
        endorser_config = await get_endorser_config(db, config_name)
        return endorser_config
    except Exception as e:
        raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post(
    "/config/{config_name}",
    status_code=status.HTTP_200_OK,
    response_model=Configuration,
)
async def update_config(
    config_name: str,
    config_value: str,
    db: AsyncSession = Depends(get_db),
) -> Configuration:
    """Update the endorser configuration for the given config name and value.

    Parameters:
        config_name (str): The name of the configuration to update.
        config_value (str): The new value for the configuration.
        db (AsyncSession): Database session dependency.

    Returns:
        Configuration: The updated configuration object.

    Raises:
        HTTPException: If an error occurs during the update process.
    """
    try:
        ConfigurationType[config_name]
        validate_endorser_config(config_name, config_value)
        endorser_config = await update_endorser_config(db, config_name, config_value)
        return endorser_config
    except Exception as e:
        raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
