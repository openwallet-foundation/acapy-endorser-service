"""This module provides async utility functions for interacting with the Aca-Py Admin API.

Functions:
- get_acapy_headers: Generates HTTP headers required for Aca-Py admin
                     API calls, including authentication tokens.
- acapy_admin_request: Makes a generic API request to the Aca-Py admin endpoint,
                       handling different HTTP methods and processing responses.
- acapy_GET: Performs a GET request on an Aca-Py tenant endpoint.
- acapy_POST: Performs a POST request on an Aca-Py tenant endpoint.
- acapy_PATCH: Performs a PATCH request on an Aca-Py tenant endpoint.
- acapy_PUT: Performs a PUT request on an Aca-Py tenant endpoint.
- acapy_DELETE: Performs a DELETE request on an Aca-Py tenant endpoint.

Usage: These functions simplify making authenticated requests to the
Aca-Py admin API, allowing easy manipulation of tenant resources in a
synchronous manner.

"""

from aiohttp import (
    ClientSession,
    ClientResponse,
)
import json

from api.config import settings


def get_acapy_headers(headers=None, tenant=False) -> dict:
    """Return HTTP headers required for aca-py admin call."""

    if not headers:
        headers = {}
    if not headers.get("accept"):
        headers["accept"] = "application/json"
    if not headers.get("Content-Type"):
        headers["Content-Type"] = "application/json"
    if settings.ACAPY_ADMIN_URL_API_KEY:
        headers["X-API-Key"] = settings.ACAPY_ADMIN_URL_API_KEY
    if settings.ACAPY_WALLET_AUTH_TOKEN:
        headers["Authorization"] = "Bearer " + settings.ACAPY_WALLET_AUTH_TOKEN
    return headers


async def acapy_admin_request(
    method, path, data=None, text=False, params=None, headers=None, tenant=False
) -> ClientResponse:
    """Generic routine to call an Aca-Py admin api.

    Default headers are used if not supplied, and security headers are injected.

    Args:
        method: http method (i.e. GET, POST, etc)
        path: endpoint path (e.g. /multitenancy/wallet)
        data: json object to POST (default None)
        text: expect a plaintext response (default False which means json response)
        params: dict of query params to include in request
        headers: dict of headers to include in the request (default None)
        tenant: whether request is in context of a tenant (default False)

    Returns:
        aiohttp response object
    """
    params = {k: v for (k, v) in (params or {}).items() if v is not None}
    url = f"{settings.ACAPY_ADMIN_URL}/{path}"

    # TODO where should this live, and how do we want to handle HTTP sessions?
    async with ClientSession() as client_session:
        headers = get_acapy_headers(headers, tenant)
        async with client_session.request(
            method,
            url,
            json=data,
            params=params,
            headers=headers,
        ) as resp:
            resp_text = await resp.text()
            try:
                resp.raise_for_status()
            except Exception as e:
                # try to retrieve and print text on error
                raise Exception(f"Error: {resp_text}") from e
            if not resp_text and not text:
                return None
            if not text:
                try:
                    return json.loads(resp_text)
                except json.JSONDecodeError as e:
                    raise Exception(f"Error decoding JSON: {resp_text}") from e
            return resp_text


async def acapy_GET(path, text=False, params=None, headers=None) -> ClientResponse:
    """Call an Aca-Py tenant endpoint using GET method."""

    response = await acapy_admin_request(
        "GET", path, data=None, text=text, params=params, headers=headers, tenant=True
    )
    return response


async def acapy_POST(
    path, data=None, text=False, params=None, headers=None
) -> ClientResponse:
    """Call an Aca-Py tenant endpoint using POST method."""

    response = await acapy_admin_request(
        "POST", path, data=data, text=text, params=params, headers=headers, tenant=True
    )
    return response


async def acapy_PATCH(path, text=False, params=None, headers=None) -> ClientResponse:
    """Call an Aca-Py tenant endpoint using PATCH method."""

    response = await acapy_admin_request(
        "PATCH", path, data=None, text=text, params=params, headers=headers, tenant=True
    )
    return response


async def acapy_PUT(
    path, data=None, text=False, params=None, headers=None
) -> ClientResponse:
    """Call an Aca-Py tenant endpoint using PUT method."""

    response = await acapy_admin_request(
        "PUT", path, data=data, text=text, params=params, headers=headers, tenant=True
    )
    return response


async def acapy_DELETE(path, text=False, headers=None) -> ClientResponse:
    """Call an Aca-Py tenant endpoint using DELETE method."""

    response = await acapy_admin_request(
        "DELETE", path, data=None, text=text, params=None, headers=headers, tenant=True
    )
    return response


# TODO in case we need them,
#  we have implemented these specific utility functions previously:
# async def admin_GET_FILE(self, path, params=None, headers=None) -> bytes:
# async def admin_PUT_FILE(self, files, url, params=None, headers=None) -> bytes:
