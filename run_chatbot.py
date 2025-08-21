#!/usr/bin/env python3
"""
BrokerBot Chatbot Launcher (Legacy - Frontend Removed)
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
import http.server
import socketserver
from pathlib import Path

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

def start_frontend_server():
    """Start the frontend server on port 8000"""
    try:
        print("🌐 Starting frontend server on port 8000...")
        
        # Get current directory
        current_dir = os.path.abspath(os.path.dirname(__file__))
        
        # Create a custom handler that serves our HTML file
        class CustomHandler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=current_dir, **kwargs)
            
            def end_headers(self):
                # Add CORS headers for ngrok compatibility
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS, PUT, DELETE')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With')
                self.send_header('Access-Control-Allow-Credentials', 'true')
                super().end_headers()
            
            def do_OPTIONS(self):
                # Handle preflight requests for ngrok
                self.send_response(200)
                self.end_headers()
            
            def log_message(self, format, *args):
                # Custom logging for better debugging
                print(f"🌐 {self.address_string()} - {format % args}")
        
        # Start server in a separate thread
        def run_server():
            with socketserver.TCPServer(("0.0.0.0", 8000), CustomHandler) as httpd:
                print("✅ Frontend server started successfully")
                print("🔗 Frontend URL: http://localhost:8000/chatbot_simple.html")
                print("🌍 Network URL: http://0.0.0.0:8000/chatbot_simple.html")
                httpd.serve_forever()
        
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        
        return server_thread
        
    except Exception as e:
        print(f"❌ Error starting frontend server: {e}")
        return None

def open_chatbot():
    """Open the chatbot in browser"""
    try:
        print("🌐 Opening chatbot in browser...")
        # Wait a moment for server to fully start
        time.sleep(2)
        webbrowser.open('http://localhost:8000/chatbot_simple.html')
    except Exception as e:
        print(f"❌ Error opening browser: {e}")

def main():
    print("=" * 50)
    print("🤖 BROKERBOT CHATBOT")
    print("=" * 50)
    
    # Start Flask API on port 5001
    api_process = start_flask_api()
    
    if api_process:
        print("✅ Flask API started on port 5001")
        
        # Start frontend server on port 8000
        frontend_server = start_frontend_server()
        
        if frontend_server:
            print("✅ Frontend server started on port 8000")
            
            # Uncomment the line below if you want automatic browser opening
            # open_chatbot()
            
            print("\n📋 INSTRUCTIONS:")
            print("1. Frontend: http://localhost:8000/chatbot_simple.html")
            print("2. API: http://localhost:5001")
            print("3. Frontend is accessible from other devices at http://YOUR_IP:8000/chatbot_simple.html")
            print("4. Each page refresh creates a new session")
            print("5. All chats are saved to MySQL database")
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
            print("❌ Failed to start frontend server")
            api_process.terminate()
    else:
        print("❌ Failed to start Flask API")
        print("💡 Make sure you have installed requirements:")
        print("   pip install -r requirements.txt")

if __name__ == "__main__":
    main() 