# iTunes XML Insights - Makefile

# Variables
COMPOSE=docker compose
PYTHON_CONTAINER=python
ES_CONTAINER=elasticsearch
KIBANA_CONTAINER=kibana

# Default target
.PHONY: help
help:
	@echo "iTunes XML Insights - Available commands:"
	@echo "  make setup        - Set up the complete system (start containers and import data)"
	@echo "  make start        - Start all containers"
	@echo "  make stop         - Stop all containers"
	@echo "  make down         - Stop and remove all containers"
	@echo "  make build        - Build the Python container"
	@echo "  make import       - Import iTunes XML data into Elasticsearch"
	@echo "  make dashboard    - Set up Kibana dashboard"
	@echo "  make restart      - Restart all containers"
	@echo "  make logs         - Show logs for all containers"
	@echo "  make clean        - Remove all containers, volumes, and networks"
	@echo "  make status       - Show status of all containers"

# Start all containers
.PHONY: start
start:
	@echo "Starting Elasticsearch and Kibana..."
	@$(COMPOSE) up -d $(ES_CONTAINER) $(KIBANA_CONTAINER)
	@echo "Containers started. Access Kibana at http://localhost:5601"

# Stop all containers
.PHONY: stop
stop:
	@echo "Stopping all containers..."
	@$(COMPOSE) stop
	@echo "Containers stopped"

# Stop and remove all containers
.PHONY: down
down:
	@echo "Stopping and removing all containers..."
	@$(COMPOSE) down
	@echo "Containers removed"

# Build the Python container
.PHONY: build
build:
	@echo "Building Python container..."
	@$(COMPOSE) build $(PYTHON_CONTAINER)
	@echo "Python container built"

# Import iTunes XML data
.PHONY: import
import:
	@echo "Importing iTunes XML data into Elasticsearch..."
	@$(COMPOSE) run --rm $(PYTHON_CONTAINER)
	@echo "Data import complete"

# Set up Kibana dashboard
.PHONY: dashboard
dashboard:
	@echo "Setting up Kibana dashboard..."
	@$(COMPOSE) run --rm $(PYTHON_CONTAINER) python -c "from kibana_setup import setup_kibana; setup_kibana()"
	@echo "Dashboard setup complete. Access at http://localhost:5601/app/dashboards#/view/itunes-analysis"

# Complete setup
.PHONY: setup
setup:
	@echo "Setting up complete system..."
	@make start
	@echo "Waiting for Elasticsearch and Kibana to start..."
	@sleep 10
	@make import
	@make dashboard
	@echo "Setup complete! Access your dashboard at http://localhost:5601/app/dashboards#/view/itunes-analysis"

# Restart all containers
.PHONY: restart
restart:
	@echo "Restarting all containers..."
	@$(COMPOSE) restart
	@echo "Containers restarted"

# Show logs for all containers
.PHONY: logs
logs:
	@$(COMPOSE) logs

# Show logs for a specific container (usage: make logs-elasticsearch, make logs-kibana, make logs-python)
.PHONY: logs-%
logs-%:
	@$(COMPOSE) logs $*

# Show status of all containers
.PHONY: status
status:
	@$(COMPOSE) ps

# Remove all Kibana saved objects
.PHONY: clean-kibana
clean-kibana:
	@echo "Removing all Kibana saved objects..."
	@$(COMPOSE) run --rm $(PYTHON_CONTAINER) python -c "from kibana_setup import delete_all_saved_objects; delete_all_saved_objects()"
	@echo "Kibana objects cleaned"

# Remove all containers, volumes, networks, and Kibana objects
.PHONY: clean
clean:
	@echo "Removing all containers, volumes, networks, and Kibana objects..."
	@make clean-kibana || true
	@$(COMPOSE) down -v
	@echo "Cleanup complete"

# Teardown and start from scratch
.PHONY: reset
reset:
	@echo "Tearing down everything and starting from scratch..."
	@make clean
	@echo "Starting containers..."
	@make start
	@echo "Waiting for services to be healthy..."
	@sleep 10
	@echo "Building Python container..."
	@make build
	@echo "Importing data..."
	@make import
	@echo "Setting up Kibana dashboard..."
	@make dashboard
	@echo "Reset complete! Access your dashboard at http://localhost:5601/app/dashboards#/view/itunes-analysis"