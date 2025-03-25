#!/bin/bash

# Make script exit on any error
set -e

echo "=== iTunes XML Insights Setup ==="
echo

# Check for Docker
if ! command -v docker >/dev/null 2>&1; then
  echo "Error: Docker is not installed. Please install Docker first."
  exit 1
fi

# Check for Docker Compose
if ! command -v docker compose >/dev/null 2>&1; then
  echo "Error: Docker Compose is not installed or not in path."
  echo "Please install Docker Compose first or use Docker Desktop which includes it."
  exit 1
fi

# Check for iTunes XML file
if [ ! -f "iTunes Music Library.xml" ]; then
  echo "Warning: 'iTunes Music Library.xml' file not found in the project directory."
  echo "Please copy this file from your iTunes folder before running the import."
  echo "Usually located at: ~/Music/iTunes/iTunes Music Library.xml"
  echo
fi

echo "Starting Docker containers..."
docker compose up -d elasticsearch kibana
echo

echo "Waiting for Elasticsearch to start (this may take a minute)..."
until $(curl --output /dev/null --silent --head --fail http://localhost:9200); do
  printf '.'
  sleep 5
done
echo
echo "Elasticsearch is running!"

echo
echo "Building and running the Python container for data import..."
docker compose build python
docker compose up python

echo
echo "Setting up Kibana dashboards..."
./setup_kibana_dashboard.sh

echo
echo "Setup complete! You can now access the iTunes dashboard at: http://localhost:5601/app/dashboards#/view/itunes-analysis"
echo