# --- Frontend Build Phase ---
# Frontend builder stage
FROM node:20-slim AS frontend-builder

WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm install

COPY frontend/ ./

# Embed the ML_SERVICE_URL into the front-end
# If not provided, then front-end will make relative calls
# e.g. localhost:8000/api/configs/
ARG ML_SERVICE_URL
RUN npx cross-env ML_SERVICE_URL=${ML_SERVICE_URL} npm run build

# --- Python Build Phase ---
# Python builder stage
FROM python:3.13-slim AS builder

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml README.md ./
COPY src/ ./src/
COPY scripts/ ./scripts/

# Install project dependencies and clean up
RUN pip install --no-cache-dir . \
    && apt-get remove -y build-essential \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/* \
    && find /usr/local/lib/python3.13 -type d -name '__pycache__' -exec rm -rf {} +

# --- Runtime Phase ---
# Runtime image
FROM python:3.13-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src \
    ML_ENVIRONMENT=production

# Install runtime dependencies and clean up
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.13/site-packages/ /usr/local/lib/python3.13/site-packages/
COPY --from=builder /usr/local/bin/ /usr/local/bin/

# Copy application code
COPY pyproject.toml ./
COPY src/ ./src/
COPY scripts/ ./scripts/

# Copy frontend build and clean up
COPY --from=frontend-builder /app/frontend/dist/ ./deployment/web/dist/
RUN rm -rf /app/frontend

# Create deployment directories (config storage, model storage)
RUN mkdir -p ./deployment/data/models ./deployment/data/configs

# Expose port
EXPOSE 8000

# Run the application
CMD ["python", "-m", "service_ml_forecast.main"]
