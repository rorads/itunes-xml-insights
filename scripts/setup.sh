#!/bin/bash
set -e

# This script automates the setup process for the iTunes XML Insights project

echo "Starting Elasticsearch and Kibana containers..."
docker compose up -d elasticsearch kibana

echo "Waiting for Elasticsearch to start (20 seconds)..."
sleep 20

echo "Setting up service accounts..."
docker compose exec elasticsearch bash /usr/share/create_service_account.sh

echo "Waiting for accounts to be created (5 seconds)..."
sleep 5

echo "Building and running Python container to import data..."
docker compose build python
docker compose run --rm python 

echo "Setup complete!"
echo "Access Kibana dashboards at: http://localhost:5601/app/dashboards#/view/itunes-analysis"