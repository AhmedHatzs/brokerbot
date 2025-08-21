#!/bin/bash

# BrokerBot API Test Script
# Tests all endpoints to ensure they work correctly

echo "🧪 Testing BrokerBot API endpoints..."
echo "======================================"

BASE_URL="http://localhost:5001"

# Test 1: Health Check
echo "1. Testing Health Check..."
curl -s -X GET "$BASE_URL/health" | jq '.'
echo ""

# Test 2: Create Session
echo "2. Creating new session..."
SESSION_RESPONSE=$(curl -s -X POST "$BASE_URL/create_session")
SESSION_ID=$(echo $SESSION_RESPONSE | jq -r '.session_id')
echo "Session created: $SESSION_ID"
echo ""

# Test 3: Send Message
echo "3. Sending test message..."
curl -s -X POST "$BASE_URL/process_message" \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"Hello, this is a test message!\", \"session_id\": \"$SESSION_ID\"}" | jq '.'
echo ""

# Test 4: Get Session Info
echo "4. Getting session info..."
curl -s -X GET "$BASE_URL/session/$SESSION_ID" | jq '.'
echo ""

# Test 5: Get Conversation History
echo "5. Getting conversation history..."
curl -s -X GET "$BASE_URL/session/$SESSION_ID/history" | jq '.'
echo ""

# Test 6: List All Sessions
echo "6. Listing all sessions..."
curl -s -X GET "$BASE_URL/sessions" | jq '.'
echo ""

# Test 7: Send Another Message
echo "7. Sending another message..."
curl -s -X POST "$BASE_URL/process_message" \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"What's the weather like today?\", \"session_id\": \"$SESSION_ID\"}" | jq '.'
echo ""

# Test 8: Get Updated History
echo "8. Getting updated conversation history..."
curl -s -X GET "$BASE_URL/session/$SESSION_ID/history" | jq '.'
echo ""

# Test 9: Test Error Handling (Invalid Session)
echo "9. Testing error handling with invalid session..."
curl -s -X POST "$BASE_URL/process_message" \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"This should fail\", \"session_id\": \"invalid-session-id\"}" | jq '.'
echo ""

# Test 10: Test Error Handling (Missing Message)
echo "10. Testing error handling with missing message..."
curl -s -X POST "$BASE_URL/process_message" \
  -H "Content-Type: application/json" \
  -d "{\"session_id\": \"$SESSION_ID\"}" | jq '.'
echo ""

echo "✅ All tests completed!"
echo "Session ID for cleanup: $SESSION_ID"
echo ""
echo "To clean up, run:"
echo "curl -X DELETE $BASE_URL/session/$SESSION_ID" 