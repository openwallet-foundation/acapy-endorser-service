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
    get_endorser_context
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
    assert (webvh_config := call_author_service(
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
    assert (log_entry := call_author_service(
        context,
        author,
        POST,
        '/did/webvh/create',
        data={
            'options': {
                'namespace': 'test',
                'identifier': identifier 
            }
        }
    ))
    put_author_context(context, author, "identifier", identifier)

@then('the witness approved the log entry')
def step_impl(context):
    pass

@then('"{author}" has a published did')
def step_impl(context, author: str):
    assert (did := call_author_service(
        context,
        author,
        GET,
        '/wallet/did',
        params={
            'method': 'webvh'
        }
    ).get('results', [])[0].get('did', None))
    assert did.split(':')[-1] == context.config.userdata[f"{author}_config"]["identifier"]
    put_author_context(context, author, "did", did)
    put_author_context(context, author, "scid", did.split(':')[2])
    assert (did_document := call_author_service(
        context,
        author,
        GET,
        f'/resolver/resolve/{did}',
    ).get('did_document', None))
    assert did_document.get('id') == did

# @when('"{author}" publishes a subsequent did log entry')
# def step_impl(context, author: str):
#     """Publish subsequent log entry."""
#     scid = get_author_context(context, author, "scid")
#     assert call_http_service(
#         'POST',
#         f'{AGENCY_BASE_URL}/did/webvh/verification-methods',
#         headers=agency_headers,
#         parameters={
#             'scid': scid
#         },
#         data={
#             'type': 'multikey'
#         }
#     )
#     did = get_author_context(context, author, "did")
#     assert (did_document := call_http_service(
#         'Get',
#         f'{AGENCY_BASE_URL}/resolver/resolve/{did}',
#         headers=agency_headers
#     ).get('did_document', {}))
#     assert len(did_document.get('verificationMethod', [])) == 2


# @when('"{author}" creates a new schema')
# def step_impl(context, author: str):
#     """Create new schema."""
#     issuer_id = get_author_context(context, author, "did")
#     assert (schema_state := call_http_service(
#         'POST',
#         f'{AGENCY_BASE_URL}/anoncreds/schema',
#         headers=agency_headers,
#         data={
#             'schema': {
#                 'attrNames': ['givenName'],
#                 'issuerId': issuer_id,
#                 'name': 'TestSchema',
#                 'version': f'1.{str(random.randrange(1000))}'
#             }
#         },
#     ).get('schema_state', {}))
#     put_author_context(context, author, "schema", schema_state.get('schema'))
#     put_author_context(context, author, "schema_id", schema_state.get('schema_id'))


# @when('"{author}" creates a new cred def')
# def step_impl(context, author: str):
#     """Create new cred def."""
#     issuer_id = get_author_context(context, author, "did")
#     schema_id = get_author_context(context, author, "schema_id")
#     assert (cred_def_state := call_http_service(
#         'POST',
#         f'{AGENCY_BASE_URL}/anoncreds/credential-definition',
#         headers=agency_headers,
#         data={
#             'credential_definition': {
#                 'issuerId': issuer_id,
#                 'schemaId': schema_id,
#                 'tag': str(uuid.uuid4())
#             }
#         },
#     ).get('credential_definition_state', {}))
#     put_author_context(
#         context, author, "cred_def", cred_def_state.get('credential_definition')
#     )
#     put_author_context(
#         context, author, "cred_def_id", cred_def_state.get('credential_definition_id')
#     )


# @when('"{author}" creates a new cred def with revocation')
# def step_impl(context, author: str):
#     """Create new cred def with revocation."""
#     issuer_id = get_author_context(context, author, "did")
#     schema_id = get_author_context(context, author, "schema_id")
#     assert (cred_def_state := call_http_service(
#         'POST',
#         f'{AGENCY_BASE_URL}/anoncreds/credential-definition',
#         headers=agency_headers,
#         data={
#             'options': {
#                 'support_revocation': True,
#                 'revocation_registry_size': 10
#             },
#             'credential_definition': {
#                 'issuerId': issuer_id,
#                 'schemaId': schema_id,
#                 'tag': str(uuid.uuid4())
#             }
#         },
#     ).get('credential_definition_state', {}))
#     put_author_context(
#         context, author, "cred_def", cred_def_state.get('credential_definition')
#     )
#     put_author_context(
#         context, author, "cred_def_id", cred_def_state.get('credential_definition_id')
#     )
