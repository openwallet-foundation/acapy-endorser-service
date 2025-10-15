"""JWT Access Token Management.

This module provides functions and classes to create and manage JWT access tokens,
including their encoding and expiration handling.
"""

from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from pydantic import BaseModel

from api.config import settings


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
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire.timestamp()})  # Convert to timestamp
    encoded_jwt = jwt.encode(
        to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )
    return AccessToken(access_token=encoded_jwt, token_type="bearer")


# OAuth2 scheme for token extraction
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/endorser/token")


def check_access_token(token: str = Depends(oauth2_scheme)) -> dict:
    """FastAPI dependency to validate JWT access token and return decoded payload.

    This function validates a JWT token by:
    1. Decoding the token using the secret key and algorithm
    2. Checking that the subject (sub) claim exists
    3. Validating that the subject matches the configured admin user
    4. Checking that the expiration (exp) claim exists
    5. Validating that the token is not expired

    Args:
        token (str): The JWT token from the Authorization header

    Returns:
        dict: The decoded token payload

    Raises:
        HTTPException: If token is invalid, expired, missing required claims,
                      or subject doesn't match configured admin user
    """

    try:
        # Decode the token
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )

        # Check if subject (sub) exists
        if not payload.get("sub"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing subject claim",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check if subject matches configured admin user
        if payload.get("sub") != settings.ENDORSER_API_ADMIN_USER:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token subject",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check if expiration (exp) exists
        if not payload.get("exp"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing expiration claim",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check if token is expired
        current_time = datetime.now(timezone.utc).timestamp()
        if payload.get("exp") < current_time:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return payload

    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token validation failed: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
