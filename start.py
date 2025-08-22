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
        'OPENAI_ASSISTANT_ID',
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
        print("⚠️  Missing environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\n💡 Some features may not work without these variables")
        print("🚀 Starting anyway for Railway deployment...")
        return True  # Continue anyway for Railway
    
    return True

def main():
    print("=" * 50)
    print("🚗 BURDY'S AUTO DETAIL CHATBOT API")
    print("=" * 50)
    
    # Check environment variables (but don't fail)
    check_environment()
    
    print("✅ Starting API server...")
    
    # Determine if we're in production (Railway) or development
    is_production = os.getenv('RAILWAY_ENVIRONMENT') == 'production'
    
    if is_production:
        print("🚀 Starting in PRODUCTION mode (Railway)")
        start_production()
    else:
        print("🔧 Starting in DEVELOPMENT mode")
        start_development()

def start_production():
    """Start the API in production mode with gunicorn optimized for Railway"""
    port = os.getenv('PORT', '5007')
    host = os.getenv('HOST', '0.0.0.0')
    
    print(f"🌐 Server will run on {host}:{port}")
    print(f"🔧 Environment: {os.getenv('RAILWAY_ENVIRONMENT', 'unknown')}")
    print(f"🔑 OpenAI API Key: {'✅ Set' if os.getenv('OPENAI_API_KEY') else '❌ Missing'}")
    print(f"🤖 OpenAI Assistant ID: {'✅ Set' if os.getenv('OPENAI_ASSISTANT_ID') else '❌ Missing'}")
    print(f"🗄️  MySQL Host: {os.getenv('MYSQL_HOST', 'Not set')}")
    
    try:
        # Railway-optimized gunicorn settings with better error handling
        subprocess.run([
            sys.executable, "-m", "gunicorn",
            "chat_api:app", 
            "--bind", f"{host}:{port}",
            "--workers", "1",  # Single worker for Railway
            "--worker-class", "sync",
            "--worker-connections", "1000",
            "--max-requests", "1000",
            "--max-requests-jitter", "50",
            "--timeout", "60",  # Increased timeout for Railway
            "--keep-alive", "2",
            "--log-level", "debug",  # More verbose logging for debugging
            "--access-logfile", "-",
            "--error-logfile", "-",
            "--preload"  # Preload app for faster startup
        ])
    except KeyboardInterrupt:
        print("\n🛑 API server stopped")
    except Exception as e:
        print(f"❌ Error starting API: {e}")
        # Exit with error code for Railway to restart
        sys.exit(1)

def start_development():
    """Start the API in development mode"""
    try:
        # Import and run Flask app directly (no subprocess)
        from chat_api import app
        
        port = int(os.getenv('PORT', 5007))
        host = os.getenv('HOST', '0.0.0.0')
        
        print(f"🌐 Server will run on {host}:{port}")
        print("🔧 Running in DEVELOPMENT mode")
        
        app.run(debug=True, host=host, port=port)
    except KeyboardInterrupt:
        print("\n🛑 API server stopped")
    except Exception as e:
        print(f"❌ Error starting API: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 