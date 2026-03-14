"""WebVH Witnessing tests."""
import uuid
import time
from behave import (
    when, given, then
)
from util import (
    GET,
    POST,
    ENDORSER_ACAPY_ADMIN_URL,
    call_http_service,
    call_author_service,
    endorser_agent_headers,
    put_author_context,
    put_endorser_context,
    get_endorser_context
)

@given("the witness plugin is configured")
def step_impl(context):
    assert (webvh_config := call_http_service(
        'POST',
        f'{ENDORSER_ACAPY_ADMIN_URL}/did/webvh/configuration',
        headers=endorser_agent_headers(context),
        data={
            'witness': True,
            'auto_attest': False,  # so requests go to API for approve/reject, not auto-attested
        }
    ))
    assert (witness_id := webvh_config.get('witnesses', [])[0])
    put_endorser_context(context, "witness_id", witness_id)

@given("the witness has an open invitation")
def step_impl(context):
    assert (invitation := call_http_service(
        'POST',
        f'{ENDORSER_ACAPY_ADMIN_URL}/did/webvh/witness-invitation',
        headers=endorser_agent_headers(context),
        data={
            'label': 'witness-service'
        }
    ))
    assert (invitation_url := invitation.get('invitation_url', None))
    put_endorser_context(context, "witness_invitation", invitation_url)

@when('"{author}" receives the invitation')
def step_impl(context, author: str):
    witness_invitation = get_endorser_context(context, 'witness_invitation')
    assert (call_author_service(
        context,
        author,
        POST,
        '/did/webvh/configuration',
        data={
            'witness': False,
            'witness_invitation': witness_invitation,
            'endorsement': True
        }
    ))

@then('"{author}" has an active witness connection')
def step_impl(context, author: str):
    assert (webvh_config := call_author_service(
        context,
        author,
        GET,
        '/did/webvh/configuration',
    ))
    assert (witness_id := webvh_config.get('witnesses', [])[0])
    assert witness_id == get_endorser_context(context, 'witness_id')


@then('"{author}" has no webvh DIDs yet')
def step_impl(context, author: str):
    """Assert wallet has no webvh DIDs before creating a log entry (rules out carryover from previous tests)."""
    response = call_author_service(
        context,
        author,
        GET,
        '/wallet/did',
        params={'method': 'webvh'},
    )
    results = response.get('results', [])
    assert results == [], (
        f"Expected no webvh DIDs before creating log entry (wallet may not be fresh), got {len(results)}: {results}"
    )


@then('"{author}" creates an initial log entry')
def step_impl(context, author: str):
    """Publish initial log entry."""
    identifier = str(uuid.uuid4())
    assert (call_author_service(
        context,
        author,
        POST,
        '/did/webvh/create',
        data={
            'options': {
                'namespace': 'test',
                'identifier': identifier,
                "witness_threshold": 1
            }
        }
    ))
    put_author_context(context, author, "identifier", identifier)

@then('the witness approved the log entry')
def step_impl(context):
    # Wait for the server to precess the log registration
    time.sleep(5)
    pass

@then('"{author}" has a published did')
def step_impl(context, author: str):
    
    # Assert DID is registered locally
    assert (results := call_author_service(
        context,
        author,
        GET,
        '/wallet/did',
        params={
            'method': 'webvh'
        }
    ).get('results', []))
    assert (did := next(iter(results), {}).get('did', None))
    assert (scid := did.split(':')[2])
    assert did.split(':')[-1] == context.config.userdata[f"{author}_config"]["identifier"]
    put_author_context(context, author, "did", did)
    put_author_context(context, author, "scid", scid)
    
    # Assert DID is resolveable
    assert (did_document := call_author_service(
        context,
        author,
        GET,
        f'/resolver/resolve/{did}',
    ).get('did_document', None))
    assert did_document.get('id') == did
    
    # Assert SCID mapping was added
    assert (call_author_service(
        context,
        author,
        GET,
        '/did/webvh/configuration',
    ).get('scids', {}).get(scid, None))

@then('the witness rejected the log entry')
def step_impl(context):
    # With ENDORSER_AUTO_ENDORSE_REQUESTS=false and ENDORSER_REJECT_BY_DEFAULT=true,
    # the endorser's auto_step_log_entry_pending calls reject_request(), which tells
    # the endorser's ACA-Py to reject the witness request. Wait for that to be
    # processed and (ideally) for the author to be notified so it does not keep a DID.
    time.sleep(5)
    pass

@then('"{author}" has no published did')
def step_impl(context, author: str):
    # Assert DID isn't registered locally (wallet/did with method=webvh)
    response = call_author_service(
        context,
        author,
        GET,
        '/wallet/did',
        params={
            'method': 'webvh'
        },
    )
    results = response.get('results', [])
    assert results == [], (
        f"Expected no webvh DIDs in wallet after rejection, got {len(results)}: {results}"
    )

    # Assert no SCID mapping was added
    config = call_author_service(
        context,
        author,
        GET,
        '/did/webvh/configuration',
    )
    scids = config.get('scids', {})
    assert scids == {}, (
        f"Expected no webvh scids after rejection, got: {scids}"
    )
