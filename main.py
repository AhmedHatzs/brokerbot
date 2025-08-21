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
    
    # FIXED: Use Config.PORT which handles Railway's PORT env var
    port = Config.PORT
    
    # FIXED: Check if running in production using new method
    if Config.is_production():
        # Production: Use Gunicorn
        print(f"🚀 Production mode: Using Gunicorn on port {port}")
        print(f"📋 API Base: http://0.0.0.0:{port}")
        print(f"🏥 Health Check: http://0.0.0.0:{port}/health")
        print(f"🌍 Environment: {'Railway' if os.getenv('PORT') else 'Production'}")
        print("=" * 50)
        
        try:
            import subprocess
            # FIXED: Railway-optimized Gunicorn settings
            subprocess.run([
                "gunicorn", 
                "--bind", f"0.0.0.0:{port}", 
                "--workers", "2",  # FIXED: Increased workers
                "--worker-class", "sync",
                "--timeout", "300",  # FIXED: Increased timeout for LLM requests
                "--keep-alive", "5",
                "--max-requests", "1000",
                "--max-requests-jitter", "100",
                "--worker-connections", "1000",
                "--preload",
                "--access-logfile", "-",  # FIXED: Log to stdout
                "--error-logfile", "-",   # FIXED: Log to stderr
                "--capture-output",
                "--enable-stdio-inheritance",
                "chat_api:app"
            ], check=True)
        except subprocess.CalledProcessError as e:
            print(f"❌ Gunicorn failed to start: {e}")
            # FIXED: Fallback to Flask if Gunicorn fails
            print("🔄 Attempting fallback to Flask development server...")
            try:
                app.run(
                    host=Config.HOST,
                    port=port,
                    debug=False,  # Never use debug in production
                    threaded=True
                )
            except Exception as fallback_error:
                print(f"❌ Flask fallback also failed: {fallback_error}")
                sys.exit(1)
        except ImportError:
            # FIXED: Handle missing Gunicorn gracefully
            print("❌ Gunicorn not available, using Flask development server")
            app.run(
                host=Config.HOST,
                port=port,
                debug=False,
                threaded=True
            )
        except Exception as e:
            print(f"❌ Unexpected error starting Gunicorn: {e}")
            # FIXED: Always attempt fallback
            print("🔄 Attempting fallback to Flask development server...")
            try:
                app.run(
                    host=Config.HOST,
                    port=port,
                    debug=False,
                    threaded=True
                )
            except Exception as fallback_error:
                print(f"❌ Flask fallback also failed: {fallback_error}")
                sys.exit(1)
    else:
        # Development: Use Flask development server
        print(f"🔧 Development mode: Using Flask development server")
        print(f"🚀 Starting server on {Config.HOST}:{port}")
        print(f"📋 API Base: http://localhost:{port}")
        print(f"🏥 Health Check: http://localhost:{port}/health")
        print("🛑 Press Ctrl+C to stop the server")
        print("=" * 50)
        
        # FIXED: Better error handling for development
        try:
            app.run(
                host=Config.HOST,
                port=port,
                debug=Config.DEBUG,
                threaded=True
            )
        except Exception as e:
            print(f"❌ Failed to start Flask development server: {e}")
            sys.exit(1) 