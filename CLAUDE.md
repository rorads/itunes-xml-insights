# iTunes XML Insights - Development Guidelines

## Project Setup
- Python version: 3.12 (specified in .python-version)
- Dockerized Elasticsearch & Kibana for data storage and visualization

## Commands
- Run application: `uv python main.py`
- Install dependencies: `uv pip install -e .`
- Lint code: `ruff check .`
- Format code: `ruff format .`
- Type check: `mypy .`
- Start containers: `docker-compose up -d`
- Stop containers: `docker-compose down`

## Code Style Guidelines
- **Formatting**: Use black-compatible formatting (via ruff)
- **Imports**: Group imports (stdlib, third-party, local) with blank lines between groups
- **Types**: Use type hints for all function parameters and return values
- **Naming**: snake_case for variables/functions, PascalCase for classes
- **Error Handling**: Use explicit try/except blocks with specific exceptions
- **Documentation**: Use docstrings for all functions, classes, and modules

## Data Processing
- Primary: Elasticsearch for ingestion and analysis of unstructured iTunes XML data
- Fallback: Use Python's ElementTree for direct XML parsing when needed
- Containerize with Docker Compose for local development and deployment