# Use official Python image
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies including SSL libraries
RUN apt-get update && apt-get install -y \
    gcc \
    openssl \
    ca-certificates \
    curl \
    netcat \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . /app

# Create conversations directory
RUN mkdir -p conversations

# Expose port (will be overridden by Railway)
EXPOSE 5007

# Set environment variables for production
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Add health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5007/health || exit 1

# Run the application
CMD ["python", "main.py"] 