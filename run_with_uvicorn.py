#!/usr/bin/env python3
"""
BrokerBot Chatbot Launcher with Uvicorn (Legacy - Frontend Removed)
This file is kept for reference but frontend functionality has been removed.
Use run_api.py for API-only deployment.
"""

import subprocess
import webbrowser
import time
import os
import threading
import signal
import sys

def start_flask_api():
    """Start the Flask API server on port 5001"""
    try:
        print("🚀 Starting Flask API server on port 5001...")
        process = subprocess.Popen([
            sys.executable, 'chat_api.py'
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        # Wait a moment for server to start
        time.sleep(3)
        
        return process
    except Exception as e:
        print(f"❌ Error starting Flask API: {e}")
        return None

def start_uvicorn_frontend():
    """Start the FastAPI frontend server with uvicorn on port 8000"""
    try:
        print("🌐 Starting FastAPI frontend with uvicorn on port 8000...")
        
        # Start uvicorn in a separate thread
        def run_uvicorn():
            subprocess.run([
                sys.executable, "-m", "uvicorn", 
                "frontend_server:app",
                "--host", "0.0.0.0",
                "--port", "8000",
                "--reload"
            ])
        
        server_thread = threading.Thread(target=run_uvicorn, daemon=True)
        server_thread.start()
        
        # Wait for server to start
        time.sleep(3)
        
        return server_thread
        
    except Exception as e:
        print(f"❌ Error starting uvicorn frontend: {e}")
        return None

def open_chatbot():
    """Open the chatbot in browser"""
    try:
        print("🌐 Opening chatbot in browser...")
        # Wait a moment for server to fully start
        time.sleep(2)
        webbrowser.open('http://localhost:8000')
    except Exception as e:
        print(f"❌ Error opening browser: {e}")

def main():
    print("=" * 50)
    print("🤖 BROKERBOT CHATBOT (UVICORN)")
    print("=" * 50)
    
    # Start Flask API on port 5001
    api_process = start_flask_api()
    
    if api_process:
        print("✅ Flask API started on port 5001")
        
        # Start uvicorn frontend on port 8000
        frontend_server = start_uvicorn_frontend()
        
        if frontend_server:
            print("✅ FastAPI frontend started with uvicorn on port 8000")
            
            # Uncomment the line below if you want automatic browser opening
            # open_chatbot()
            
            print("\n📋 INSTRUCTIONS:")
            print("1. Frontend: http://localhost:8000")
            print("2. API: http://localhost:5001")
            print("3. Frontend is accessible from other devices at http://YOUR_IP:8000")
            print("4. Ngrok: ngrok http 8000")
            print("5. Each page refresh creates a new session")
            print("6. All chats are saved to MySQL database")
            print("\n🛑 Press Ctrl+C to stop both servers")
            
            try:
                # Keep the script running
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n🛑 Shutting down...")
                api_process.terminate()
                api_process.wait()
                print("✅ Servers stopped")
        else:
            print("❌ Failed to start uvicorn frontend")
            api_process.terminate()
    else:
        print("❌ Failed to start Flask API")
        print("💡 Make sure you have installed requirements:")
        print("   pip install -r requirements.txt")

if __name__ == "__main__":
    main() 