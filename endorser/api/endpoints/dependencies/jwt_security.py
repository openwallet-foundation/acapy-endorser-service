"""JWT Access Token Management.

This module provides functions and classes to create and manage JWT access tokens,
including their encoding and expiration handling.
"""

from datetime import datetime, timedelta

from jose import jwt
from pydantic import BaseModel

from api.core.config import settings


class AccessToken(BaseModel):
    """Model representing an access token and its type."""

    access_token: str
    token_type: str


def create_access_token(data: dict):
    """Create a JWT access token with an expiration time and return it.

    This function generates a JSON Web Token (JWT) by encoding the provided data
    with a predefined expiration time. The token is then returned as an
    AccessToken object with a 'bearer' type.

    Args:
        data (dict): The data to be encoded in the token.

    Returns:
        AccessToken: An object containing the access token and its type.
    """
    expires_delta = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )
    return AccessToken(access_token=encoded_jwt, token_type="bearer")
