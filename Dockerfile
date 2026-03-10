FROM python:3.11-slim

WORKDIR /app

# Install uv for fast dependency resolution
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files first for layer caching
COPY pyproject.toml uv.lock ./
COPY adk-fluent/ ./adk-fluent/

# Install dependencies
RUN uv sync --frozen --no-dev

# Copy application code
COPY server.py ./
COPY network_outage_agent/ ./network_outage_agent/
COPY static/ ./static/
COPY .env ./

EXPOSE 8080

CMD ["uv", "run", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8080"]
