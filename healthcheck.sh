#!/bin/bash
# Health check script for Railway deployment
# Reads PORT from environment and checks the health endpoint

# Get port from environment or default to 5007
PORT=${PORT:-5007}

echo "🔍 Health check for port ${PORT}"

# Try root endpoint first (simplest, no database required)
echo "📡 Testing root endpoint..."
if curl -f --max-time 10 http://localhost:${PORT}/; then
    echo "✅ Root endpoint is healthy"
    exit 0
fi

# Fallback to ping endpoint
echo "📡 Testing /ping endpoint..."
if curl -f --max-time 10 http://localhost:${PORT}/ping; then
    echo "✅ /ping endpoint is healthy"
    exit 0
fi

# Fallback to health endpoint
echo "📡 Testing /health endpoint..."
if curl -f --max-time 15 http://localhost:${PORT}/health; then
    echo "✅ /health endpoint is healthy"
    exit 0
fi

echo "❌ All health checks failed"
exit 1 