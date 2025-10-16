"""This module sets up the authentication routes for the Endorser service."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from api.config import settings
from api.endpoints.dependencies.jwt_security import AccessToken, create_access_token

router = APIRouter(tags=["auth"])


@router.post("/token", response_model=AccessToken)
async def login_for_endorser_api_admin(
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    """Authenticate an Endorser API Admin and return an access token.

    This endpoint receives the admin user's credentials through an OAuth2
    password request form. If successfully authenticated, it will generate
    an access token for the user. If authentication fails, it raises an
    HTTP 401 Unauthorized exception.

    Parameters:
        form_data (OAuth2PasswordRequestForm): Form containing username and password.

    Returns:
        AccessToken: A token provided upon successful authentication.

    Raises:
        HTTPException: If authentication fails.
    """
    authenticated = await authenticate_endorser(form_data.username, form_data.password)
    if not authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect Endorser Api Admin User or Endorser Api Admin Key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return create_access_token(data={"sub": form_data.username})


async def authenticate_endorser(username: str, password: str) -> bool:
    """Authenticate the endorser using provided username and password credentials.

    This function checks if the given username and password match the
    pre-defined admin credentials for the endorser API. It returns True if the
    credentials are valid, otherwise returns False.

    Args:
        username (str): The username to authenticate.
        password (str): The password to authenticate.

    Returns:
        bool: True if authentication is successful, otherwise False.
    """
    return (
        settings.ENDORSER_API_ADMIN_USER == username
        and settings.ENDORSER_API_ADMIN_KEY == password
    )
