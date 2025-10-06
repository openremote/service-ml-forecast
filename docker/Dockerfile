# --- Frontend Build Phase -----------------------------------------------------
FROM node:20-slim AS frontend-builder

RUN echo "Starting frontend build phase..."

WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN echo "Installing frontend dependencies..."
RUN npm install

COPY frontend/ ./

# Define build arguments
ARG ML_SERVICE_URL
ARG ML_WEB_ROOT_PATH
ARG ML_OR_KEYCLOAK_URL
ARG ML_OR_URL

# Run the front-end bundle in production mode
RUN ML_SERVICE_URL=${ML_SERVICE_URL:-/services/ml-forecast} \
    ML_WEB_ROOT_PATH=${ML_WEB_ROOT_PATH:-/services/ml-forecast/ui} \
    ML_OR_KEYCLOAK_URL=${ML_OR_KEYCLOAK_URL:-/auth} \
    ML_OR_URL=${ML_OR_URL:-} \
    npm run build:prod

# --- Python Build Phase -------------------------------------------------------
FROM python:3.13-slim AS builder

RUN echo "Starting Python build phase..."

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN echo "Installing Python build dependencies..."
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Copy the necessary project files
COPY pyproject.toml uv.lock README.md ./
COPY src/ ./src/
COPY scripts/ ./scripts/
COPY packages/ ./packages/

# Install project dependencies using uv
RUN echo "Installing Python project dependencies..."
RUN uv sync --no-cache-dir \
    && apt-get remove -y build-essential \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/* \
    && find /usr/local/lib/python3.13 -type d -name '__pycache__' -exec rm -rf {} +

# --- Runtime Phase ------------------------------------------------------------
FROM python:3.13-slim

RUN echo "Starting runtime phase setup..."

WORKDIR /app

# Explicitly declare the ARG for the build process
ARG ML_ENVIRONMENT

# Add git commit label must be specified at build time using --build-arg GIT_COMMIT=commit-hash
ARG GIT_COMMIT=unknown
LABEL git-commit=$GIT_COMMIT

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src \
    ML_ENVIRONMENT=${ML_ENVIRONMENT:-production}

# Install any runtime dependencies
RUN echo "Installing runtime dependencies..."
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager
RUN pip install uv

# Copy application code
COPY pyproject.toml uv.lock README.md ./
COPY src/ ./src/
COPY scripts/ ./scripts/
COPY packages/ ./packages/

# Install project dependencies using uv
RUN echo "Installing Python project dependencies..."
RUN uv sync --no-cache-dir

# Copy frontend build artifacts
RUN echo "Copying frontend build artifacts..."
COPY --from=frontend-builder /app/frontend/dist/ ./deployment/web/dist/
RUN rm -rf /app/frontend

# Create deployment directories (config storage, model storage)
RUN echo "Creating deployment directories..."
RUN mkdir -p ./deployment/data/models ./deployment/data/configs

# Expose port
EXPOSE 8000

# Add health check
HEALTHCHECK --interval=10s --timeout=10s --start-period=30s --retries=3 CMD curl --fail --silent http://localhost:8000/ui || exit 1

RUN echo "Container setup complete! Starting application..."

# Run the application using uv run to ensure virtual environment is activated
CMD ["uv", "run", "python", "-m", "service_ml_forecast.main"]
