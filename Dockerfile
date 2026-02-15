# Use slim Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system dependencies (only if required)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    libssl-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for caching)
COPY requirements.txt .

# Upgrade pip and install dependencies globally
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .
RUN chmod +x start.sh
# Create non-root user (security best practice)
RUN useradd -m appuser && chown -R appuser:appuser /app

USER appuser

# Build argument for port (defaults to 8080 for dev, 8081 for prod)
ARG PORT=8080
ENV PORT=${PORT}

EXPOSE ${PORT}

# Healthcheck (uses PORT env variable, defaults to 8080)
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD sh -c 'port=$${PORT:-8080} && curl -f http://localhost:$$port/health || exit 1'

# Start application
CMD ["./start.sh"]

