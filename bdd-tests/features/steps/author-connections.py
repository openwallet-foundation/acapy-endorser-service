import time
import os
import pprint
import random

from behave import *

from util import (
    authenticate_endorser_service,
    call_endorser_service,
    call_agency_service,
    call_author_service,
    set_endorser_config,
    set_endorser_author_connection_config,
    set_endorser_author_connection_info,
    get_endorsers_author_connection,
    get_authors_endorser_connection,
    GET,
    POST,
    ENDORSER_URL_PREFIX,
    get_author_context,
    put_author_context,
    clear_author_context,
    get_endorser_context,
    put_endorser_context,
)

MAX_INC = 10
SLEEP_INC = 2


@given("the endorser service is running")
def step_impl(context):
    # check that the endorser service is running
    endorser_status = call_endorser_service(context, GET, "/")
    assert endorser_status["status"] == "ok", pprint.pp(endorser_status)

    # authenticate the service and save our auth token
    endorser_auth_status = authenticate_endorser_service(context)
    assert endorser_auth_status["Authorization"].startswith("Bearer "), pprint.pp(
        endorser_auth_status
    )

    # set "auto" configs to False
    resp = set_endorser_config(context, "ENDORSER_AUTO_ACCEPT_CONNECTIONS", "false")
    resp = set_endorser_config(context, "ENDORSER_REJECT_BY_DEFAULT", "false")
    resp = set_endorser_config(context, "ENDORSER_AUTO_ACCEPT_AUTHORS", "false")
    resp = set_endorser_config(context, "ENDORSER_AUTO_ENDORSE_REQUESTS", "false")
    resp = set_endorser_config(
        context, "ENDORSER_AUTO_ENDORSE_TXN_TYPES", "1,100,101,102,113,114"
    )


@given("the endorser has a well-known public DID")
def step_impl(context):
    # fetch the endorser public DID and save in context
    endorser_config = call_endorser_service(
        context, GET, f"{ENDORSER_URL_PREFIX}/admin/config"
    )
    assert "public_did" in endorser_config["endorser_config"], pprint.pp(
        endorser_config
    )

    # save for future reference
    endorser_did = endorser_config["endorser_config"]["public_did"]
    put_endorser_context(context, "endorser_did", endorser_did)


@given('the endorser has "{config_name}" configured as "{config_value}"')
def step_impl(context, config_name: str, config_value: str):
    resp = set_endorser_config(context, config_name, config_value)
    assert resp["config_value"] == config_value, pprint.pp(resp)


@given(
    'the endorser has "{author}" connection info "{author_alias}" and "{public_did}"'
)
def step_impl(context, author: str, author_alias: str, public_did: str):
    resp = set_endorser_author_connection_info(
        context, author, author_alias, public_did
    )
    assert resp["author_status"] == author_status, pprint.pp(resp)
    assert resp["public_did"] == public_did, pprint.pp(resp)


@given(
    'the endorser has "{author}" connection configuration "{author_status}" and "{endorse_status}"'
)
def step_impl(context, author: str, author_status: str, endorse_status: str):
    resp = set_endorser_author_connection_config(
        context, author, author_status, endorse_status
    )
    assert resp["author_status"] == author_status, pprint.pp(resp)
    assert resp["endorse_status"] == endorse_status, pprint.pp(resp)


@given('there is a new author agent "{author}"')
def step_impl(context, author: str):
    # create (and authenticate) a new author agent
    clear_author_context(context, author)

    rand_suffix = ("000000" + str(random.randint(1, 100000)))[-6:]
    author_name = f"{author}_{rand_suffix}"
    data = {
        "key_management_mode": "managed",
        "label": author_name,
        "wallet_key": author_name,
        "wallet_name": author_name,
        "wallet_type": "askar",
    }

    author_wallet = call_agency_service(
        context, POST, "/multitenancy/wallet", data=data
    )
    assert "token" in author_wallet, pprint.pp(author_wallet)

    put_author_context(context, author, "wallet", author_wallet)

    # try calling the author wallet
    author_config = call_author_service(context, author, GET, "/status/config")
    assert "config" in author_config, pprint.pp(author_config)


@given('"{author}" connects to the endorser using their public DID')
@when('"{author}" connects to the endorser using their public DID')
def step_impl(context, author: str):
    # request a connection from the author to the endorser via public DID
    endorser_public_did_config = get_endorser_context(context, "endorser_did")
    endorser_public_did = endorser_public_did_config["did"]
    endorser_alias = os.getenv("AUTHOR_ENDORSER_AlIAS")
    connection_request = call_author_service(
        context,
        author,
        POST,
        "/didexchange/create-request",
        params={
            "their_public_did": endorser_public_did,
            "alias": endorser_alias,
        },
    )
    assert "connection_id" in connection_request, pprint.pp(connection_request)

    # save the endorser connection request
    put_author_context(context, author, "endorser_connection", connection_request)


@given('the endorser accepts "{author}" connection request')
@when('the endorser accepts "{author}" connection request')
def step_impl(context, author: str):
    # find the connection request from "author"
    author_wallet = get_author_context(context, author, "wallet")
    author_alias = author_wallet["settings"]["default_label"]
    author_conn_request = None
    inc = 0
    while not author_conn_request:
        connection_requests = call_endorser_service(
            context,
            GET,
            f"{ENDORSER_URL_PREFIX}/connections",
            params={"state": "request"},
        )
        for connection in connection_requests["connections"]:
            if connection["their_label"] == author_alias:
                author_conn_request = connection
        if (not author_conn_request) or (not author_conn_request["state"] == "request"):
            time.sleep(1)
            inc += 1
            assert inc < MAX_INC, f"Error too many retries can't find {author_alias}"

    assert author_conn_request, f"Error no connection request from {author_alias}"

    # endorser accept the connection request
    auth_conn_id = author_conn_request["connection_id"]
    resp = call_endorser_service(
        context, POST, f"{ENDORSER_URL_PREFIX}/connections/{auth_conn_id}/accept"
    )

    # verify meta-data on the connection
    # TODO not exposed through the endorser api (yet) ...


@given('"{author}" sets endorser meta-data on the connection')
@when('"{author}" sets endorser meta-data on the connection')
def step_impl(context, author: str):
    # find the endorser connection for this author
    connection_request = get_author_context(context, author, "endorser_connection")
    connection_id = connection_request["connection_id"]
    endorser_connection = None
    inc = 0
    while not endorser_connection:
        endorser_connection = call_author_service(
            context, author, GET, f"/connections/{connection_id}"
        )
        if not endorser_connection:
            time.sleep(1)
            inc += 1
            assert inc < MAX_INC, pprint.pp(endorser_connection)
    assert endorser_connection, pprint.pp(endorser_connection)

    # author set meta-data on the connection
    endorser_name = endorser_connection["alias"]
    endorser_public_did_config = get_endorser_context(context, "endorser_did")
    endorser_public_did = endorser_public_did_config["did"]
    time.sleep(2)
    resp = call_author_service(
        context,
        author,
        POST,
        f"/transactions/{connection_id}/set-endorser-role",
        params={"transaction_my_job": "TRANSACTION_AUTHOR"},
    )
    resp = call_author_service(
        context,
        author,
        POST,
        f"/transactions/{connection_id}/set-endorser-info",
        params={
            "endorser_did": endorser_public_did,
            "endorser_name": endorser_name,
        },
    )


@given('"{author}" has an "{connection_status}" connection to the endorser')
@then('"{author}" has an "{connection_status}" connection to the endorser')
def step_impl(context, author: str, connection_status: str):
    # verify the state of the author connection
    connection_request = get_author_context(context, author, "endorser_connection")
    connection_id = connection_request["connection_id"]
    endorser_connection = get_authors_endorser_connection(
        context, author, connection_id, connection_status
    )

    assert endorser_connection["state"] == connection_status, pprint.pp(
        endorser_connection
    )


@given('the endorser has an "{connection_status}" connection with "{author}"')
@then('the endorser has an "{connection_status}" connection with "{author}"')
def step_impl(context, connection_status: str, author: str):
    # verify the state of the endorser connection
    author_wallet = get_author_context(context, author, "wallet")
    author_alias = author_wallet["settings"]["default_label"]
    author_conn_request = get_endorsers_author_connection(
        context, author_alias, connection_status
    )

    assert author_conn_request["state"] == connection_status, pprint.pp(
        author_conn_request
    )


## COMPOSED ACTIONS
@given('There is a new agent "{author}" that is connected to the endorser')
def step_impl(context, author):
    context.execute_steps(
        f"""
            Given the endorser service is running
            And the endorser has a well-known public DID
            And there is a new author agent "{author}"
            And "{author}" connects to the endorser using their public DID
            And the endorser accepts "{author}" connection request
            And "{author}" sets endorser meta-data on the connection
            And "{author}" has an "active" connection to the endorser
            And the endorser has an "active" connection with "{author}"
        """
    )


## COMPOSED ACTIONS
@given(
    'There is a new agent "{author}" that is connected to the endorser (with auto-accept)'
)
def step_impl(context, author):
    context.execute_steps(
        f"""
            Given the endorser service is running
            And the endorser has "ENDORSER_AUTO_ACCEPT_CONNECTIONS" configured as "true"
            And the endorser has a well-known public DID
            And there is a new author agent "{author}"
            And "{author}" connects to the endorser using their public DID
            And "{author}" sets endorser meta-data on the connection
            And "{author}" has an "active" connection to the endorser
            And the endorser has an "active" connection with "{author}"
        """
    )
