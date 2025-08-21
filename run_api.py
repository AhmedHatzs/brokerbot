#!/usr/bin/env python3
"""
BrokerBot API Launcher
Starts the Flask API server only (no frontend)
"""

import subprocess
import time
import sys
import signal

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

def main():
    print("=" * 50)
    print("🤖 BROKERBOT API SERVER")
    print("=" * 50)
    
    # Start Flask API on port 5001
    api_process = start_flask_api()
    
    if api_process:
        print("✅ Flask API started on port 5001")
        
        print("\n📋 API ENDPOINTS:")
        print("1. API Base: http://localhost:5001")
        print("2. Process Message: POST http://localhost:5001/process_message")
        print("3. Health Check: GET http://localhost:5001/health")
        print("4. API is accessible from other devices at http://YOUR_IP:5001")
        print("\n🛑 Press Ctrl+C to stop the server")
        
        try:
            # Keep the script running
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Shutting down...")
            api_process.terminate()
            api_process.wait()
            print("✅ Server stopped")
    else:
        print("❌ Failed to start Flask API")
        print("💡 Make sure you have installed requirements:")
        print("   pip install -r requirements.txt")

if __name__ == "__main__":
    main() 