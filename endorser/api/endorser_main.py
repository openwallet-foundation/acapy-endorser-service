"""This module configures a FastAPI application for an Endorser service with OAuth2."""

import logging

from fastapi import APIRouter, Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from starlette.middleware import Middleware
from starlette_context import plugins
from starlette_context.middleware import RawContextMiddleware

from api.endpoints.routes.endorser_api import endorser_router
from api.endpoints.dependencies.jwt_security import AccessToken, create_access_token
from api.core.config import settings as s


logger = logging.getLogger(__name__)

middleware = [
    Middleware(
        RawContextMiddleware,
        plugins=(plugins.RequestIdPlugin(), plugins.CorrelationIdPlugin()),
    ),
]

router = APIRouter()


def get_endorserapp() -> FastAPI:
    """Create and configure the FastAPI application for the Endorser service.

    This function initializes a FastAPI application with configurations
    for middleware, token endpoint, and other secured endpoints.
    It sets up routers and applies necessary dependencies and tags.

    Returns:
        FastAPI: The configured FastAPI application instance.
    """
    application = FastAPI(
        title=s.TITLE,
        description=s.DESCRIPTION,
        debug=s.DEBUG,
        middleware=middleware,
    )
    # mount the token endpoint
    application.include_router(router, prefix="")
    # mount other endpoints, these will be secured by the above token endpoint
    application.include_router(
        endorser_router,
        prefix=s.API_V1_STR,
        dependencies=[Depends(OAuth2PasswordBearer(tokenUrl="token"))],
        tags=["endorser"],
    )
    return application


@router.post("/token", response_model=AccessToken)
async def login_for_traction_api_admin(
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
    return s.ENDORSER_API_ADMIN_USER == username and s.ENDORSER_API_ADMIN_KEY == password
