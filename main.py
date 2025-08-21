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
    
    # Check if running in production (Railway sets PORT environment variable)
    if os.getenv('PORT'):
        # Production: Use Gunicorn
        port = int(os.getenv('PORT'))
        print(f"🚀 Production mode: Using Gunicorn on port {port}")
        print(f"📋 API Base: http://0.0.0.0:{port}")
        print(f"🏥 Health Check: http://0.0.0.0:{port}/health")
        print("=" * 50)
        import subprocess
        subprocess.run([
            "gunicorn", 
            "--bind", f"0.0.0.0:{port}", 
            "--workers", "1",
            "--timeout", "120",
            "chat_api:app"
        ])
    else:
        # Development: Use Flask development server
        print(f"🔧 Development mode: Using Flask development server")
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