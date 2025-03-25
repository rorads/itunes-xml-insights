#!/bin/bash

# Make script exit on any error
set -e

echo "=== Setting up iTunes XML Insights Kibana Dashboard ==="
echo

# Check if Kibana is running and healthy
if ! docker compose ps kibana | grep -q "healthy"; then
  echo "Waiting for Kibana to be healthy..."
  until docker compose ps kibana | grep -q "healthy"; do
    echo -n "."
    sleep 5
  done
  echo
  echo "Kibana is healthy!"
fi

echo "Running Kibana setup script..."
# Run the Python container with our kibana_setup script
docker compose run --rm python python -c "from kibana_setup import setup_kibana; setup_kibana()"

echo
echo "Setup complete! Access your iTunes dashboard at: http://localhost:5601/app/dashboards#/view/itunes-analysis"
echo