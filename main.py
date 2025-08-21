#!/usr/bin/env python3
"""
BrokerBot - Main Entry Point
A trading assistant chatbot with conversation memory
"""

from chat_api import app
from config import Config
import os
import sys

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
        
        try:
            import subprocess
            # Use more conservative Gunicorn settings for Railway
            subprocess.run([
                "gunicorn", 
                "--bind", f"0.0.0.0:{port}", 
                "--workers", "1",
                "--timeout", "120",
                "--keep-alive", "5",
                "--max-requests", "1000",
                "--max-requests-jitter", "100",
                "--preload",
                "chat_api:app"
            ], check=True)
        except subprocess.CalledProcessError as e:
            print(f"❌ Gunicorn failed to start: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Unexpected error starting Gunicorn: {e}")
            sys.exit(1)
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