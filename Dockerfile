# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY pyproject.toml .
COPY README.md .

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Copy source code
COPY src/ ./src/

# Create data directories
RUN mkdir -p /app/data /app/quarantine /app/schemas

# Expose ports
EXPOSE 8000
EXPOSE 8080

# Set environment variables
ENV PYTHONPATH=/app/src
ENV TICKDB_DATA_PATH=/app/data
ENV TICKDB_QUARANTINE_PATH=/app/quarantine

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Default command
CMD ["python", "-m", "tickdb.cli", "--help"] 