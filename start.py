#!/usr/bin/env python3
"""
Railway-friendly startup script for Burdy's Auto Detail Chatbot API
Handles both development and production environments
"""

import os
import sys
import subprocess
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def check_environment():
    """Check if all required environment variables are set"""
    required_vars = [
        'OPENAI_API_KEY',
        'MYSQL_HOST',
        'MYSQL_PORT',
        'MYSQL_DATABASE',
        'MYSQL_USER',
        'MYSQL_PASSWORD'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\n💡 Please set these variables in Railway environment")
        return False
    
    return True

def main():
    print("=" * 50)
    print("🚗 BURDY'S AUTO DETAIL CHATBOT API")
    print("=" * 50)
    
    # Check environment variables
    if not check_environment():
        sys.exit(1)
    
    print("✅ Environment variables configured")
    
    # Determine if we're in production (Railway) or development
    is_production = os.getenv('RAILWAY_ENVIRONMENT') == 'production' or os.getenv('PORT') is not None
    
    if is_production:
        print("🚀 Starting in PRODUCTION mode (Railway)")
        start_production()
    else:
        print("🔧 Starting in DEVELOPMENT mode")
        start_development()

def start_production():
    """Start the API in production mode with gunicorn"""
    port = os.getenv('PORT', '5007')
    host = os.getenv('HOST', '0.0.0.0')
    
    print(f"🌐 Server will run on {host}:{port}")
    
    try:
        # Use gunicorn for production (proper WSGI server for Flask)
        subprocess.run([
            sys.executable, "-m", "gunicorn",
            "chat_api:app", 
            "--bind", f"{host}:{port}",
            "--workers", "1",
            "--log-level", "info",
            "--timeout", "120"
        ])
    except KeyboardInterrupt:
        print("\n🛑 API server stopped")
    except Exception as e:
        print(f"❌ Error starting API: {e}")

def start_development():
    """Start the API in development mode"""
    try:
        # Use Flask development server
        subprocess.run([sys.executable, "chat_api.py"])
    except KeyboardInterrupt:
        print("\n🛑 API server stopped")
    except Exception as e:
        print(f"❌ Error starting API: {e}")

if __name__ == "__main__":
    main() 