#!/bin/bash
set -e

# Get elastic password from environment or use default
ELASTIC_PASSWORD=${ELASTIC_PASSWORD:-secure_password_123}
echo "Using elastic password: ${ELASTIC_PASSWORD}"

echo "Waiting for Elasticsearch to be available..."
until curl -s -u elastic:${ELASTIC_PASSWORD} http://localhost:9200 > /dev/null; do
    sleep 1
done

echo "Creating kibana_service_account role..."
curl -X PUT "localhost:9200/_security/role/kibana_service_account" \
     -u elastic:${ELASTIC_PASSWORD} \
     -H 'Content-Type: application/json' -d'
{
  "cluster": ["monitor", "manage_index_templates", "manage_ml", "manage", "manage_ingest_pipelines"],
  "indices": [
    {
      "names": ["*", ".kibana*"],
      "privileges": ["read", "view_index_metadata", "write", "manage", "create_index", "create", "all"]
    }
  ],
  "applications": [
    {
      "application": "kibana-.kibana",
      "privileges": ["*"],
      "resources": ["*"]
    }
  ]
}
'

echo "Creating kibana_service_user user..."
curl -X PUT "localhost:9200/_security/user/kibana_service_user" \
     -u elastic:${ELASTIC_PASSWORD} \
     -H 'Content-Type: application/json' -d'
{
  "password" : "kibana_service_password",
  "roles" : [ "kibana_service_account", "kibana_system", "kibana_admin" ],
  "full_name" : "Kibana Service Account"
}
'

echo "Service account created successfully."
echo "Username: kibana_service_user"
echo "Password: kibana_service_password"