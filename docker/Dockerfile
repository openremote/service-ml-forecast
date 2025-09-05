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
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 

RUN echo "Installing Python build dependencies..."
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml README.md ./
COPY src/ ./src/
COPY scripts/ ./scripts/

# Install project dependencies and clean up
RUN echo "Installing Python project dependencies..."
RUN pip install --no-cache-dir . \
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

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src \
    # Use the ARG, falling back to a default if not provided during build or runtime
    ML_ENVIRONMENT=${ML_ENVIRONMENT:-production}

# Install runtime dependencies and clean up
RUN echo "Installing runtime dependencies..."
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
RUN echo "Copying Python packages from builder..."
COPY --from=builder /usr/local/lib/python3.13/site-packages/ /usr/local/lib/python3.13/site-packages/
COPY --from=builder /usr/local/bin/ /usr/local/bin/

# Copy application code
COPY pyproject.toml ./
COPY src/ ./src/
COPY scripts/ ./scripts/

# Copy frontend build and clean up
RUN echo "Copying frontend build artifacts..."
COPY --from=frontend-builder /app/frontend/dist/ ./deployment/web/dist/
RUN rm -rf /app/frontend

# Create deployment directories (config storage, model storage)
RUN echo "Creating deployment directories..."
RUN mkdir -p ./deployment/data/models ./deployment/data/configs

# Expose port
EXPOSE 8000

# Add health check
HEALTHCHECK --interval=5s --timeout=5s --start-period=30s --retries=3 CMD curl --fail --silent http://localhost:8000/ui || exit 1

RUN echo "Container setup complete! Starting application..."

# Run the application
CMD ["python", "-m", "service_ml_forecast.main"]
