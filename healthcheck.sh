#!/bin/bash
# Health check script for Railway deployment
# Reads PORT from environment and checks the health endpoint

# Get port from environment or default to 5007
PORT=${PORT:-5007}

# Perform health check
curl -f --max-time 5 http://localhost:${PORT}/health || exit 1 