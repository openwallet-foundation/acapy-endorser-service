"""WebVH Witnessing tests."""
import random
import uuid
import time
import pprint
from behave import (
    when, given, then
)
from util import (
    GET,
    POST,
    WEBVH_SERVER_URL,
    AGENCY_BASE_URL,
    ENDORSER_BASE_URL,
    ENDORSER_URL_PREFIX,
    ENDORSER_ACAPY_ADMIN_URL,
    AUTHOR_ACAPY_ADMIN_URL,
    call_http_service,
    call_author_service,
    call_agency_service,
    call_endorser_service,
    agency_headers,
    endorser_headers,
    endorser_agent_headers,
    put_author_context,
    get_author_context,
    put_endorser_context,
    get_endorser_context,
    set_endorser_config
)

@given("the witness plugin is configured")
def step_impl(context):
    assert (webvh_config := call_http_service(
        'POST',
        f'{ENDORSER_ACAPY_ADMIN_URL}/did/webvh/configuration',
        headers=endorser_agent_headers(context),
        data={
            'witness': True
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
                "witnessThreshold": 1
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
    print(results)
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
    # Wait for the server to process the log registration
    time.sleep(5)
    pass

@then('"{author}" has no published did')
def step_impl(context, author: str):
    # Assert DID isn't registered locally
    assert (results := call_author_service(
        context,
        author,
        GET,
        '/wallet/did',
        params={
            'method': 'webvh'
        }
    ).get('results', [])) == []
    assert (next(iter(results), {}).get('did', None)) is None
    
    # # Assert DID is not resolveable
    # TODO, resolve did web?
    # assert (did_document := call_author_service(
    #     context,
    #     author,
    #     GET,
    #     f'/resolver/resolve/{did}',
    # ).get('did_document', None))
    # assert did_document.get('id') == did
    
    # Assert no SCID mapping was added
    assert (call_author_service(
        context,
        author,
        GET,
        '/did/webvh/configuration',
    ).get('scids', {})) == {}
