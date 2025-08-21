# Use official Python image
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . /app

# Create conversations directory
RUN mkdir -p conversations

# Expose port
EXPOSE 5001

# Set environment variables for production
ENV PYTHONUNBUFFERED=1

# Run the application with Gunicorn for production
CMD ["gunicorn", "--bind", "0.0.0.0:5001", "chat_api:app"] 