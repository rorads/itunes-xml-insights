FROM python:3.12-slim

WORKDIR /app

# Install curl for healthchecks
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Install uv for faster Python dependency management
RUN pip install --no-cache-dir uv

# Copy pyproject.toml for dependency installation
COPY pyproject.toml .

# Install dependencies directly (not in a venv)
RUN uv pip install --system -e .

# Copy the application code
COPY . .

# Run as non-root user for security
RUN useradd -m appuser
RUN chown -R appuser:appuser /app
USER appuser

# Run the application
CMD ["python", "main.py"]