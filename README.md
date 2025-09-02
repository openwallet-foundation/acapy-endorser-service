[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Lifecycle:Maturing](https://img.shields.io/badge/Lifecycle-Maturing-007EC6)](https://github.com/bcgov/repomountie/blob/master/doc/lifecycle-badges.md)

# Aries - Endorser Service

This repository provides an Endoser agent, based on [Aries Cloudagent Python (or Aca-Py)](https://github.com/hyperledger/aries-cloudagent-python).

Information about Aca-Py's Endorser support can be found [here](https://github.com/hyperledger/aries-cloudagent-python/blob/main/Endorser.md).

The Aca-Py Alice/Faber demo also demonstrates the use of the Endorser feature, as described [here](https://github.com/hyperledger/aries-cloudagent-python/blob/main/demo/Endorser.md).

This repository is a work in progress, see [this document](https://hackmd.io/hWMLdpu7SBuopNag4mTbcg?view) for the ongoing requirements and design.

## Running Locally

Prerequisites - you can run a local von-network and tails server, or connect to an existing service.

To run everything locally, open 2 bash shells and run the following:

```bash
git clone https://github.com/bcgov/von-network.git
cd von-network
./manage build
./manage start --logs
```

```bash
git clone https://github.com/bcgov/indy-tails-server.git
cd indy-tails-server/docker
./manage build
./manage start --logs
```

Then, to get the endorser service up and running quickly, open a bash shell and run the following:

```bash
git clone https://github.com/bcgov/aries-endorser-service.git
cd aries-endorser-service/docker
./manage build
./manage start --logs
```

**Note:** if running in the devcontainer, two folders have been prepared to check-out von-network and indy-tails server in the `/workspaces` directory.

You can open the Endorser Admin API in your browser at http://localhost:5050/endorser/docs - you will need to authenticate using the configured ID and password (endorser-admin/change-me). (The webhooks API is at http://localhost:5050/webhook/docs, although you shouldn't need to use this one directly.)

To shut down the service:

```bash
<ctrl-c>
./manage rm
```

By default, the Endorser runs with a local ledger and tails server.

To run against the BCovrin Test ledger (http://test.bcovrin.vonx.io/) and tails server (https://tails-test.vonx.io), start the endorser using the `LEDGER_URL` and `TAILS_SERVER_URL` parameters:

```bash
LEDGER_URL=http://test.bcovrin.vonx.io TAILS_SERVER_URL=https://tails-test.vonx.io ./manage start --logs
```

You can also use the `GENESIS_URL` parameter to run against a non-von-network ledger. For example, the SOVRIN staging ledger's transactions can be found [here](https://raw.githubusercontent.com/sovrin-foundation/sovrin/master/sovrin/pool_transactions_sandbox_genesis).

```bash
GENESIS_URL=https://raw.githubusercontent.com/sovrin-foundation/sovrin/master/sovrin/pool_transactions_sandbox_genesis ./manage start --logs
```

(And, with the above, you need to provide a suitable tails server parameter.)

By default, the `./manage` script will use a random seed to generate the Endorser's public DID. Author agents will need to know this public DID to create transactions for endorsement. If you need to start the Endorser using a "well-known DID" you can start with the `ENDORSER_SEED` parameter:

```bash
ENDORSER_SEED=<your 32 char seed> ./manage start --logs
```

To define a WebVH server to use, set the `WEBVH_SERVER_URL` variable.

```bash
WEBVH_SERVER_URL=https://id.test-suite.app
```

## Exposing the Endorser Agent using Ngrok

By default, the `./manage` script will start an ngrok process to expose the Endorser agent's endpoint, and the Endorser agent will use the ngrok URL when publishing their endpoint.

### Auth

Each developer must apply for an Ngrok token [here](https://dashboard.ngrok.com/get-started/your-authtoken). Then place the token into an `.env` file within the **docker** directory with the contents below.

```
NGROK_AUTHTOKEN=<your token here>
```

### Bypassing Ngrok

If you don't want to do this (or if ngrok isn't workin' for ya) you can override this behaviour - just set environment variable `ENDORSER_ENV` to something other than `local`, and then set `ACAPY_ENDPOINT` explicitly.

For example, to startup the Endorser to run exclusively within a docker network (for example to run the BDD tests ... see later section ...):

```bash
ENDORSER_ENV=testing ACAPY_ENDPOINT=http://host.docker.internal:8050 ./manage start-bdd --logs
```

## BREAKING CHANGES

Note that as of the latest version all connection_id's in the contact table is expected to be unique. If upgrading fails with an error similar to 
```
sqlalchemy.exc.IntegrityError: (psycopg2.errors.UniqueViolation) could not create unique index "contact_connection_id_key"
```
then you will need to manually delete these duplicate entries. To list them you can perform the following sql query

```
select * from contact
group by contact_id, connection_id
having COUNT(distinct(connection_id)) > 1
```

## Endorser Configuration

Three "global" configuration options can be set using environment variables or can be set using the Endorser Admin API, the environment variables are:

- `ENDORSER_AUTO_ACCEPT_CONNECTIONS`: set to `true` for the Endorser service to auto-accept connections (otherwise they must be manually accepted)
- `ENDORSER_AUTO_ACCEPT_AUTHORS`: set to `true` for the Endorser service to auto-configure new connections to be "authors", otherwise author meta-data must be manually set
- `ENDORSER_AUTO_ENDORSE_REQUESTS`: set to `true` for the Endorser service to auto-accept all "endorse transaction" requests (otherwise they must be manually endorsed)
- `ENDORSER_REJECT_BY_DEFAULT`: set to `true` for the Endorser service to auto-reject any "endorse transaction" request that cannot automatically be endorsed (see granular auto-endorse configuration)

These parameters can be set using the `POST /endorser/v1/admin/config/<env var name>?config_value=<value>` admin API, and the setting is stored in the database (the database setting will override the environment variable). You can see the configured values using the `GET /endorser/v1/admin/config/<env var name>` endpoint (and it will let you know if the configuration is using a value from the database or environment variable).

There are 2 endpoints to set connection-specific (i.e. author-specific) configuration.

`PUT /endorser/v1/connections/<connection_id>` - sets the alias and (optionally) public DID for the author (not currently used anywhere by the Endorser, but may be useful).

`PUT /endorser/v1/connections/<connection_id>/configure` - sets processing options for the connection:

- `author_status` - `Active` or `Suspended` - if not Active, all requests from this connection will be ignored
- `endorse_status` - `AutoEndorse`, `ManualEndorse` or `AutoReject` - the "auto" options will automatically endorse or refuse endorsement requests (respectively), for the "manual" option the requests must be manually endorsed

Endorsement requests will be auto-endorsed if the `ENDORSER_AUTO_ENDORSE_REQUESTS` setting is `true` _or_ if the `endorse_status` is set to `AutoEndorse` on the connection. So, if manual endorsements are desired, `ENDORSER_AUTO_ENDORSE_REQUESTS` should be set to `false` _and_ each connection should be set to `ManualEndorse` (which is the default).


### Granular Configuration of Auto Endorsement

Auto endorsement of transactions is configured via the `/allow/{publish-data,schema,credential-definition}` endpoints

Each endpoint supports a `GET`, `POST` and `DELETE` for listing the
allowed automatically endorsable transactions, adding new transactions to be automatically endorsed, and deleting transactions.

Any requests using the `POST` method support using "\*" to indicate a
wild card.

#### Configuration with CSV files

Auto endorsement of transactions can be configured via the `/allow/config` endpoints

This endpoint supports `PUT` and `POST` which will allow you to bulk modify a list of allowed automatically endorsable transactions.

- POST: This method will replace the current configuration with the data from the uploaded CSV file.

- PUT: In contrast, the PUT method appends the data from the CSV file to the existing configuration, preserving the current state.

Each of these endpoints supports uploading a CSV file for `publish-data`, schema, and `credential-definition`.

The fields of these CSVs follow the format used in the `POST /allow/{publish-data,schema,credential-definition}` endpoints

For example, the description for the `POST /allow/`schema` endpoint and the CSV equivalent is

| Name          | Description | Default |
| ------------- | ----------- | ------- |
| `author_did`  | string      | \*      |
| `schema_name` | string      | \*      |
| `version`     | string      | \*      |
| `details`     | string      | null    |

and the CSV equivalent is

```csv
author_did,schema_name,version,details
3fa85f64-5717-4562-b3fc-2c963f66afa6,myschema,1.0,Some details
9d885f64-5717-4562-b3fc-2c963f66adl1,myschema,2.0,Other details
```

NOTE: The header (aka `author_did,schema_name,version`) is used to identify each of the fields

To append this to the Endorser's list of allowed schemas the
corresponding curl command would be

```sh
curl -X 'PUT' \
  'http://ENDORSERURL/v1/allow/config' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer YOUR_TOKEN_HERE' \
  -H 'Content-Type: multipart/form-data' \
  -F 'publish_did=' \
  -F 'schema=@YOURFILE.csv' \
  -F 'credential_definition='
```

For the updated descriptions of the allow lists start the endorser service and open http://localhost:5050/endorser/docs in your browser

The `POST /allow/`{publish-data,` `schema``,credential-definition`}` describes the corresponding CSV file format.

#### CSV Input Description

##### public_did

| Name             | Description | Default |
| ---------------- | ----------- | ------- |
| `registered_did` | string      | "\*"    |
| `details`        | string      | null    |

Example

```csv
registered_did,details
5NzdaLiTEpvy5MK5fLiBMV,A public DID
5NzdaLiTEpvy5MK5fLiBMV,Same public DID
```

##### schema

| Name          | Description | Default |
| ------------- | ----------- | ------- |
| `author_did`  | string      | "\*"    |
| `schema_name` | string      | "\*"    |
| `version`     | string      | "\*"    |
| `details`     | string      | null    |

Example:

```csv
author_did,schema_name,version,details
5NzdaLiTEpvy5MK5fLiBMV,myschema,1.0,My test schema
```

##### credential_definition

| Name                 | Description | Default |
|----------------------|-------------|---------|
| `schema_issuer_did`  | string      | "\*"    |
| `creddef_author_did` | string      | "\*"    |
| `schema_name`        | string      | "\*"    |
| `version`            | string      | "\*"    |
| `tag`                | string      | "\*"    |
| `rev_reg_def`        | boolean     | True    |
| `rev_reg_entry`      | boolean     | True    |
| `details`            | string      | null    |

Example:

```csv
schema_issuer_did,creddef_author_did,schema_name,version,tag,rev_reg_def,rev_reg_entry,details
5NzdaLiTEpvy5MK5fLiBMV,4NzdaLiTEpvy5MK5fLiBMV,demoschema,2.0,test_tag,True,False,My test credential definition
```

**NOTE**: `schema_issuer_did` is the DID of the creator of the schema the credential definition is based on. `creddef_author_did` is the DID of the creator of this credential definition

## Testing - Integration tests using Behave

This repository includes integration tests implemented using Behave.

When you start the endorser service, you can optionally start an additional Author agent which is used for testing:

```bash
./manage start-bdd --logs
```

Or, if you want to connect to the wallet directly (rather than using a ngrok-exposed port), run this instead:

```bash
ENDORSER_ENV=bdd ./manage start-bdd --logs
```

The Author agent (which is configured as multi-tenant) exposes its Admin API on http://localhost:8061/api/doc

You can run the BDD tests in a docker container by running:

```bash
./manage run-bdd-docker
```

... or to run a specific test (or group of tests), for example:

```bash
./manage run-bdd-docker -t @DIDs-006
```

Or (historically) you can run the BDD tests locally.  Note that you need python version `3.12` or better installed locally.

Open a second bash shell within the poetry environment (cd to the directory where you have checked out this repository) and run the BDD tests with:

```bash
LEDGER_URL=http://localhost:9000 TAILS_SERVER_URL=http://localhost:6543 ./manage run-bdd
```

... or to run a specific test (or group of tests), for example:

```bash
LEDGER_URL=http://localhost:9000 TAILS_SERVER_URL=http://localhost:6543 ./manage run-bdd -t @DIDs-006
```

For the WebVH tests, define the webvh server url:

```bash
WEBVH_SERVER_URL=https://sandbox.bcvh.vonx.io ./manage run-bdd -t @Witnessing-001
```

To enter the poetry environment you can make use of [devcontainers](https://containers.dev/)  or simply run `poetry shell`

Note that because these tests run on your local (rather than in a docker container) you need to specify the _local_ URL to the ledger and tails servers.

## Testing - Other

You can also test using [traction](https://github.com/bcgov/traction).

(Note that this describes the "old" traction integration tests. There are new tests in traction using behave, this doc should be updated to reflect the latest traction.)

Open a bash shell and startup the endorser services:

```bash
git clone https://github.com/bcgov/aries-endorser-service.git
cd aries-endorser-service/docker
./manage build
# note we start with a "known" endorser DID
# ... and we need to point to the same ledger and tails server as traction ...
ENDORSER_SEED=testendorserseed_123123123123123 LEDGER_URL=<...> TAILS_SERVER_URL=<...> ./manage start --logs
```

Then open a separate bash shell and run the following:

```bash
git clone https://github.com/bcgov/traction.git
cd traction/scripts
git checkout endorser-integration
cp .env-example .env
docker-compose build
docker-compose up
```

Then open up yet another bash shell and run the traction integration tests. Traction tenants will connect to the endorser service for creating schemas, credential definitions etc.

```bash
cd <traction/scripts directory from above>
docker exec scripts_traction-api_1 pytest --asyncio-mode=strict -m integtest
```

... or you can run individual tests like this:

```bash
docker exec scripts_traction-api_1 pytest --asyncio-mode=strict -m integtest tests/integration/endpoints/routes/test_tenant.py::test_tenant_issuer
```

Traction integration tests create new tenants for each test, so you can rebuild/restart the endorser service without having to restart traction.

# Credit

The initial implementation of the Aries Endorser Service was developed by the Government of British Columbia’s Digital Trust Team in Canada, and is based on [aries-cloudagent-python](https://github.com/hyperledger/aries-cloudagent-python) and [traction](https://github.com/bcgov/traction). To learn more about what’s happening with decentralized identity and digital trust in British Columbia, check out https://digital.gov.bc.ca/digital-trust.

# Additional resources

Example OpenShift configurations for deploying an Aries Endorser Service instance can be found in the [Aries Endorser Configurations](https://github.com/bcgov/dts-endorser-service) project.

# Contributing

Pull requests are welcome! Please read our [contributions guide](CONTRIBUTING.md) and submit your PRs. We enforce [developer certificate of origin](https://developercertificate.org/) (DCO) commit signing. See guidance [here](https://github.com/apps/dco).

## Becoming a maintainer

Refer to the [Maintainers](MAINTAINERS.md) document for details.

## Logging bugs, issues, and feature requests

To log bugs/issues/feature requests, please file an [issue](../../issues).

## Reporting security issues

Please refer to the [Hyperledger Security Policy](SECURITY.md) for details.

# License

[Apache License Version 2.0](LICENSE)
