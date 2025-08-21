#!/usr/bin/env python3
"""
BrokerBot - Main Entry Point
A trading assistant chatbot with conversation memory
"""

from chat_api import app
from config import Config
import os

if __name__ == "__main__":
    print("=" * 50)
    print("🤖 BROKERBOT")
    print("=" * 50)
    print(f"🚀 Starting server on {Config.HOST}:{Config.PORT}")
    print(f"📋 API Base: http://localhost:{Config.PORT}")
    print(f"🏥 Health Check: http://localhost:{Config.PORT}/health")
    print("🛑 Press Ctrl+C to stop the server")
    print("=" * 50)
    
    # Check if running in production (Railway sets PORT environment variable)
    if os.getenv('PORT'):
        # Production: Use Railway's PORT
        port = int(os.getenv('PORT'))
        print(f"🚀 Production mode: Using Railway port {port}")
        app.run(host="0.0.0.0", port=port, debug=False)
    else:
        # Development: Use Flask development server
        print("🔧 Development mode: Using Flask development server")
        app.run(
            host=Config.HOST,
            port=Config.PORT,
            debug=Config.DEBUG
        ) 