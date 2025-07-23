#!/bin/bash

# based on code developed by Sovrin:  https://github.com/hyperledger/aries-acapy-plugin-toolbox

if [[ "${ENDORSER_ENV}" == "local" ]]; then
	echo "using ngrok end point [$NGROK_NAME]"

	NGROK_ENDPOINT=null
	while [ -z "$NGROK_ENDPOINT" ] || [ "$NGROK_ENDPOINT" = "null" ]
	do
	    echo "Fetching end point from ngrok service"
	    NGROK_ENDPOINT=$(curl --silent $NGROK_NAME:4040/api/tunnels | ./jq -r '.tunnels[] | select(.proto=="https") | .public_url')

	    if [ -z "$NGROK_ENDPOINT" ] || [ "$NGROK_ENDPOINT" = "null" ]; then
	        echo "ngrok not ready, sleeping 5 seconds...."
	        sleep 5
	    fi
	done

	export ACAPY_ENDPOINT=$NGROK_ENDPOINT
fi

echo "Starting aca-py agent with endpoint [$ACAPY_ENDPOINT]"

# ... if you want to echo the aca-py startup command ...
set -x

exec aca-py start \
    --auto-provision \
    --inbound-transport http '0.0.0.0' ${ACAPY_HTTP_PORT} \
    --inbound-transport ws '0.0.0.0' ${ACAPY_WS_PORT} \
    --outbound-transport http \
    --outbound-transport ws \
    --webhook-url "${ENDORSER_WEBHOOK_URL}" \
    --genesis-url "${GENESIS_URL}" \
    --tails-server-base-url "${TAILS_SERVER_URL}" \
    --notify-revocation \
    --monitor-revocation-notification \
    --endpoint "${ACAPY_ENDPOINT}" \
    --auto-ping-connection \
    --monitor-ping \
    --public-invites \
    --wallet-type "askar" \
    --wallet-name "${ACAPY_WALLET_DATABASE}" \
    --wallet-key "${ACAPY_WALLET_ENCRYPTION_KEY}" \
    --wallet-storage-type "${ACAPY_WALLET_STORAGE_TYPE}" \
    --wallet-storage-config "{\"url\":\"${POSTGRESQL_HOST}:5432\",\"max_connections\":5}" \
    --wallet-storage-creds "{\"account\":\"${POSTGRESQL_USER}\",\"password\":\"${POSTGRESQL_PASSWORD}\",\"admin_account\":\"${POSTGRESQL_USER}\",\"admin_password\":\"${POSTGRESQL_PASSWORD}\"}" \
    --wallet-name "${ACAPY_WALLET_DATABASE}"  \
    --seed "${ENDORSER_SEED}" \
    --admin '0.0.0.0' ${ACAPY_ADMIN_PORT} \
    --label "${AGENT_NAME}" \
    ${ACAPY_ADMIN_CONFIG} \
    --endorser-protocol-role endorser \
    --log-level "${LOG_LEVEL}" \
    --plugin webvh \
    --plugin-config-value "did-webvh.server_url=${WEBVH_SERVER_URL}"
