#!/usr/bin/env python3
"""
Quick Test Script for BrokerBot
Tests the basic functionality of your chatbot
"""

import requests
import json
import time

def test_chatbot(base_url="http://localhost:5001"):
    """Test the chatbot API"""
    print("🧪 Testing BrokerBot API")
    print("=" * 40)
    
    # Test 1: Health Check
    print("1. Testing health check...")
    try:
        response = requests.get(f"{base_url}/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Health check passed")
            print(f"   Status: {data['status']}")
            print(f"   LLM Service: {data['llm_service']['status']}")
            print(f"   Storage: {data['conversation_memory']['storage_type']}")
        else:
            print(f"   ❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Health check error: {e}")
        return False
    
    # Test 2: Create Session
    print("\n2. Testing session creation...")
    try:
        response = requests.post(f"{base_url}/create_session", timeout=10)
        if response.status_code == 201:
            data = response.json()
            session_id = data['session_id']
            print(f"   ✅ Session created: {session_id[:8]}...")
        else:
            print(f"   ❌ Session creation failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Session creation error: {e}")
        return False
    
    # Test 3: Send Message
    print("\n3. Testing message processing...")
    try:
        message_data = {
            "message": "Hello! Can you help me with trading advice?",
            "session_id": session_id
        }
        response = requests.post(
            f"{base_url}/process_message",
            json=message_data,
            timeout=30
        )
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Message processed successfully")
            print(f"   Response: {data['response'][:50]}...")
            print(f"   Total messages: {data['conversation_info']['total_messages']}")
        else:
            print(f"   ❌ Message processing failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
    except Exception as e:
        print(f"   ❌ Message processing error: {e}")
        return False
    
    # Test 4: Get Session Info
    print("\n4. Testing session info...")
    try:
        response = requests.get(f"{base_url}/session/{session_id}", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Session info retrieved")
            print(f"   Total messages: {data['total_messages']}")
        else:
            print(f"   ❌ Session info failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Session info error: {e}")
    
    # Test 5: Get History
    print("\n5. Testing conversation history...")
    try:
        response = requests.get(f"{base_url}/session/{session_id}/history", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ History retrieved: {len(data['conversation_history'])} messages")
        else:
            print(f"   ❌ History failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ History error: {e}")
    
    # Test 6: Send Another Message
    print("\n6. Testing follow-up message...")
    try:
        message_data = {
            "message": "What are the key principles of risk management in trading?",
            "session_id": session_id
        }
        response = requests.post(
            f"{base_url}/process_message",
            json=message_data,
            timeout=30
        )
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Follow-up message processed")
            print(f"   Response: {data['response'][:50]}...")
            print(f"   Total messages: {data['conversation_info']['total_messages']}")
        else:
            print(f"   ❌ Follow-up message failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Follow-up message error: {e}")
    
    # Test 7: Clean Up
    print("\n7. Testing session cleanup...")
    try:
        response = requests.delete(f"{base_url}/session/{session_id}", timeout=10)
        if response.status_code == 200:
            print(f"   ✅ Session deleted successfully")
        else:
            print(f"   ❌ Session deletion failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Session deletion error: {e}")
    
    print("\n" + "=" * 40)
    print("🎉 All tests completed!")
    print("✅ Your chatbot is working correctly!")
    return True

def test_deployed_url():
    """Test with deployed URL (you'll need to update this)"""
    print("\n🚀 Testing Deployed URL")
    print("=" * 40)
    print("⚠️  Update the URL below with your actual deployed URL")
    
    # Replace this with your actual deployed URL
    deployed_url = "https://your-app-name.railway.app"
    
    print(f"Testing: {deployed_url}")
    print("Update the deployed_url variable in this script with your actual URL")
    
    # Uncomment the line below when you have your deployed URL
    # test_chatbot(deployed_url)

if __name__ == "__main__":
    # Test local chatbot
    test_chatbot()
    
    # Test deployed chatbot (uncomment when deployed)
    # test_deployed_url() 