import json
import time
import os
import pprint
import random
import time

from behave import *
from starlette import status

from util import (
    authenticate_endorser_service,
    call_endorser_service,
    call_agency_service,
    call_author_service,
    call_http_service,
    set_endorser_config,
    get_endorsers_author_connection,
    get_authors_endorser_connection,
    get_endorser_transaction_record,
    get_author_transaction_record,
    GET,
    POST,
    HEAD,
    ENDORSER_URL_PREFIX,
    get_author_context,
    put_author_context,
    clear_author_context,
    get_endorser_context,
    put_endorser_context,
    clear_endorser_context,
)


MAX_INC = 10
SLEEP_INC = 2
LEDGER_URL = os.getenv("LEDGER_URL")


@when('"{author}" creates a new local DID in their wallet')
def step_impl(context, author: str):
    # POST /wallet/did/create with payload {} (returns {"result": {"did": "...", ...}})
    resp = call_author_service(
        context,
        author,
        POST,
        "/wallet/did/create",
        data={},
    )
    assert "result" in resp, pprint.pp(resp)
    assert resp["result"]["did"], pprint.pp(resp)
    # save in context
    put_author_context(context, author, "wallet_did", resp["result"])


@when('"{author}" initiates an out of band process to register their DID')
def step_impl(context, author: str):
    # get did from context
    author_wallet_did = get_author_context(context, author, "wallet_did")
    # use von-network to register the did (out of band process)
    resp = call_http_service(
        POST,
        f"{LEDGER_URL}/register",
        {
            "accept": "application/json",
            "Content-Type": "application/json",
        },
        data={
            "did": author_wallet_did["did"],
            "verkey": author_wallet_did["verkey"],
            "role": None,
        },
    )
    # check that a did was created
    assert "did" in resp, pprint.pp(resp)


@when('"{author}" registers their new DID on the ledger')
def step_impl(context, author: str):
    # get did from context
    author_wallet = get_author_context(context, author, "wallet")
    author_wallet_did = get_author_context(context, author, "wallet_did")
    # POST /ledger/register-nym
    params = {
        "did": author_wallet_did["did"],
        "verkey": author_wallet_did["verkey"],
        "alias": author_wallet["settings"]["wallet.name"],
    }
    resp = call_author_service(
        context,
        author,
        POST,
        "/ledger/register-nym",
        params=params,
    )
    assert "txn" in resp, pprint.pp(resp)
    assert "transaction_id" in resp["txn"], pprint.pp(resp)
    # save into context
    put_author_context(context, author, "current_transaction", resp["txn"])


@when('"{author}" sets the new DID to be their wallet public DID')
def step_impl(context, author: str):
    # get did from context
    author_wallet_did = get_author_context(context, author, "wallet_did")
    # POST /wallet/did/public
    resp = call_author_service(
        context,
        author,
        POST,
        "/wallet/did/public",
        params={"did": author_wallet_did["did"]},
    )
    assert "txn" in resp, pprint.pp(resp)
    assert "transaction_id" in resp["txn"], pprint.pp(resp)
    # save into context
    put_author_context(context, author, "current_transaction", resp["txn"])


@when('the endorser receives an endorsement request from "{author}"')
def step_impl(context, author: str):
    # get transaction from context
    txn_request = get_author_context(context, author, "current_transaction")
    tnx_id = txn_request["transaction_id"]

    # get endorser's author connection
    author_wallet = get_author_context(context, author, "wallet")
    author_alias = author_wallet["settings"]["default_label"]
    author_conn = get_endorsers_author_connection(context, author_alias)
    connection_id = author_conn["connection_id"]

    endorser_txn = get_endorser_transaction_record(context, connection_id, "request_received")

    # confirm this is from the current "active" author connection
    assert author_conn["connection_id"] == endorser_txn["connection_id"], pprint.pp(author_conn)
    assert "request_received" == endorser_txn["state"], pprint.pp(author_conn)
    put_endorser_context(context, f"{author}/current_transaction", endorser_txn)


@when('the endorser endorses the transaction from "{author}"')
def step_impl(context, author: str):
    # get transaction from context
    txn_request = get_endorser_context(context, f"{author}/current_transaction")
    tnx_id = txn_request["transaction_id"]

    # POST /v1/endorse/transactions/<txn id>/endorse
    resp = call_endorser_service(
        context,
        POST,
        f"{ENDORSER_URL_PREFIX}/endorse/transactions/{tnx_id}/endorse",
    )
    pass


@when('the endorser rejects the transaction from "{author}"')
def step_impl(context, author: str):
    # get transaction from context
    txn_request = get_endorser_context(context, f"{author}/current_transaction")
    tnx_id = txn_request["transaction_id"]

    # POST /v1/endorse/transactions/<txn id>/reject
    resp = call_endorser_service(
        context,
        POST,
        f"{ENDORSER_URL_PREFIX}/endorse/transactions/{tnx_id}/reject",
    )
    pass


@when('"{author}" receives the endorsed transaction from the endorser')
@then('"{author}" receives the endorsed transaction from the endorser')
def step_impl(context, author: str):
    # get transaction info from context
    txn_request = get_author_context(context, author, "current_transaction")
    tnx_id = txn_request["transaction_id"]

    # check state - wait for it to be written (we have auto write)
    author_txn = get_author_transaction_record(context, author, tnx_id, "transaction_acked")
    assert author_txn, pprint.pp(author_txn)


@when('"{author}" receives the rejected transaction from the endorser')
def step_impl(context, author: str):
    # get transaction info from context
    txn_request = get_author_context(context, author, "current_transaction")
    tnx_id = txn_request["transaction_id"]

    # check state - wait for it to be written (we have auto write)
    author_txn = get_author_transaction_record(context, author, tnx_id, "transaction_refused")
    assert author_txn, pprint.pp(author_txn)


@given('"{author}" has a public DID')
@then('"{author}" has a public DID')
def step_impl(context, author: str):
    # GET /wallet/did/public
    # get did from context
    author_wallet_did = get_author_context(context, author, "wallet_did")
    resp = call_author_service(
        context,
        author,
        GET,
        f"/wallet/did/public",
    )
    public_did = resp["result"]
    assert public_did["did"], pprint.pp(public_did)
    assert public_did["did"] == author_wallet_did["did"], pprint.pp(public_did)


@then('"{author}" has a transaction with status "{txn_state}"')
def step_impl(context, author: str, txn_state: str):
    # get transaction info from context
    txn_request = get_author_context(context, author, "current_transaction")
    tnx_id = txn_request["transaction_id"]

    # check state - wait for it to be written (we have auto write)
    author_txn = get_author_transaction_record(context, author, tnx_id, txn_state)
    assert author_txn, pprint.pp(author_txn)


## COMPOSED ACTIONS
@given('There is a new agent "{author}" that is connected to the endorser and has a public DID')
def step_impl(context, author):
    context.execute_steps(
        f"""
            Given There is a new agent "{author}" that is connected to the endorser
            And "{author}" has an "active" connection to the endorser
            And the endorser has an "active" connection with "{author}"
            When "{author}" creates a new local DID in their wallet
            And "{author}" initiates an out of band process to register their DID
            And "{author}" sets the new DID to be their wallet public DID
            And the endorser receives an endorsement request from "{author}"
            And the endorser endorses the transaction from "{author}"
            And "{author}" receives the endorsed transaction from the endorser
            Then "{author}" has a public DID
        """
    )


@given('There is a new agent "{author}" that is connected to the endorser and has a public DID (with auto accept)')
def step_impl(context, author):
    context.execute_steps(
        f"""
            Given There is a new agent "{author}" that is connected to the endorser (with auto-accept)
            And "{author}" has an "active" connection to the endorser
            And the endorser has an "active" connection with "{author}"
            And the endorser has "{author}" connection configuration "Active" and "AutoEndorse"
            When "{author}" creates a new local DID in their wallet
            And "{author}" initiates an out of band process to register their DID
            And "{author}" sets the new DID to be their wallet public DID
            And "{author}" receives the endorsed transaction from the endorser
            Then "{author}" has a public DID
        """
    )
