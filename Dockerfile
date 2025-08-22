# Use official Python image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy requirements first for better caching
COPY requirements.txt /app/

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . /app/

# Make healthcheck script executable
RUN chmod +x /app/healthcheck.sh

# Create non-root user for security
RUN adduser --disabled-password --gecos '' appuser && chown -R appuser:appuser /app
USER appuser

# Expose the API port (Railway will set PORT environment variable)
EXPOSE 5007

# Health check with shorter timeout - uses Railway's PORT environment variable
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=5 \
    CMD ./healthcheck.sh

# Use the production-ready startup script
CMD ["python", "start.py"] 