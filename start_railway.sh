#!/bin/bash

# Railway startup script
# This script properly handles the PORT environment variable

# Set default port if not provided
PORT=${PORT:-5007}

echo "🚀 Starting Burdy's Auto Detail Chatbot API on port $PORT"

# Start gunicorn with the correct port
exec gunicorn chat_api:app \
    --bind 0.0.0.0:$PORT \
    --workers 1 \
    --worker-class sync \
    --timeout 60 \
    --keep-alive 2 \
    --log-level debug \
    --access-logfile - \
    --error-logfile - 