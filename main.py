#!/usr/bin/env python3
"""
BrokerBot - Main Entry Point
A trading assistant chatbot with conversation memory
"""

from chat_api import app
from config import Config

if __name__ == "__main__":
    print("=" * 50)
    print("🤖 BROKERBOT")
    print("=" * 50)
    print(f"🚀 Starting server on {Config.HOST}:{Config.PORT}")
    print(f"📋 API Base: http://localhost:{Config.PORT}")
    print(f"🏥 Health Check: http://localhost:{Config.PORT}/health")
    print("🛑 Press Ctrl+C to stop the server")
    print("=" * 50)
    
    app.run(
        host=Config.HOST,
        port=Config.PORT,
        debug=Config.DEBUG
    ) 