#!/usr/bin/env python3
"""
Test script to verify BrokerBot works with in-memory storage
"""

import os
import sys

# Force in-memory storage for testing
os.environ['FORCE_MEMORY_STORAGE'] = 'true'

# Import after setting environment variable
from chat_api import app
from config import Config

def test_memory_storage():
    """Test the application with in-memory storage"""
    print("🧪 Testing BrokerBot with in-memory storage...")
    
    # Print configuration
    print(f"Storage Type: {Config.get_storage_type()}")
    print(f"Force Memory: {Config.FORCE_MEMORY_STORAGE}")
    
    # Test basic functionality
    with app.test_client() as client:
        # Test root endpoint
        response = client.get('/')
        print(f"Root endpoint status: {response.status_code}")
        
        # Test health endpoint
        response = client.get('/health')
        print(f"Health endpoint status: {response.status_code}")
        
        # Test session creation
        response = client.post('/create_session', json={})
        print(f"Create session status: {response.status_code}")
        
        if response.status_code == 201:
            data = response.get_json()
            session_id = data.get('session_id')
            print(f"Session created: {session_id}")
            
            # Test message processing
            payload = {
                "message": "Hello! This is a test message.",
                "session_id": session_id
            }
            response = client.post('/process_message', json=payload)
            print(f"Process message status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.get_json()
                print(f"Bot response: {data.get('response', 'N/A')[:100]}...")
                print("✅ All tests passed!")
            else:
                print(f"❌ Message processing failed: {response.get_data()}")
        else:
            print(f"❌ Session creation failed: {response.get_data()}")
    
    print("\n🎉 In-memory storage test completed!")

if __name__ == "__main__":
    test_memory_storage() 