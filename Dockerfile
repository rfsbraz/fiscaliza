# Standard Flask application for ECS Fargate
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies including PostgreSQL client
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir psycopg2-binary gunicorn

# Copy application code
COPY app/ ./app/
COPY database/ ./database/
COPY config/ ./config/

# Copy script files (exclude downloads and large data directories)
COPY scripts/data_processing/*.py ./scripts/data_processing/
COPY scripts/data_processing/mappers/ ./scripts/data_processing/mappers/
COPY scripts/data_processing/utils/ ./scripts/data_processing/utils/
COPY scripts/database/ ./scripts/database/
COPY scripts/analysis/ ./scripts/analysis/
COPY scripts/analytics/ ./scripts/analytics/
COPY scripts/utilities/ ./scripts/utilities/
COPY scripts/deploy/ ./scripts/deploy/
# Copy individual Python files from scripts root
COPY scripts/*.py ./scripts/

# Create static directory for frontend files if they exist
RUN mkdir -p ./app/static/dist/

# Set Python path
ENV PYTHONPATH=/app

# Database configuration for PostgreSQL RDS
ENV DATABASE_TYPE=postgresql
ENV DATABASE_NAME=parliament

# Flask configuration
ENV FLASK_ENV=production
ENV FLASK_DEBUG=0
ENV LOG_LEVEL=INFO

# Application configuration
ENV PORT=80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:80/api/ping || exit 1

# Expose port 80 for CloudFlare Flexible SSL
EXPOSE 80

# Note: Running as root to bind to port 80. Container is protected by:
# - AWS Security Groups (only CloudFlare IPs allowed)
# - VPC network isolation
# For production with non-root user, use ALB for SSL termination

# Start Flask application with Gunicorn on port 80
CMD ["gunicorn", "--bind", "0.0.0.0:80", "--workers", "2", "--timeout", "120", "--keep-alive", "5", "app.main:app"]