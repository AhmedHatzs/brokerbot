# 🚀 BrokerBot API Reference

This document provides complete API documentation for integrating your frontend application with the BrokerBot chatbot service.

## 🔗 Base URL
```
http://localhost:5001
```

## 📋 API Endpoints Overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Check API health status |
| POST | `/create_session` | Create new conversation session |
| POST | `/process_message` | Send message to chatbot |
| GET | `/session/{session_id}` | Get session information |
| GET | `/session/{session_id}/history` | Get conversation history |
| GET | `/sessions` | List all sessions |
| DELETE | `/session/{session_id}` | Delete a session |
| POST | `/cleanup_sessions` | Clean up expired sessions |

## 🔧 CORS Support
✅ **CORS is enabled** for all routes, allowing frontend applications from any domain to connect.

---

## 📝 Detailed API Documentation

### 1. Health Check
**`GET /health`**

Check if the API is running and get system status.

**Response:**
```json
{
  "status": "API is running",
  "conversation_memory": {
    "storage_type": "MySQLStorage",
    "total_sessions": 5,
    "max_context_tokens": 4000,
    "max_tokens_per_chunk": 2000
  },
  "llm_service": {
    "status": "healthy",
    "info": {
      "assistant_id": "asst_xxxxx...",
      "model": "gpt-3.5-turbo",
      "max_tokens": 1000,
      "temperature": 0.7
    }
  },
  "timestamp": "2025-08-22T01:00:00.000000"
}
```

---

### 2. Create Session
**`POST /create_session`**

Create a new conversation session. **Always call this first** before sending messages.

**Request:**
```http
POST /create_session
Content-Type: application/json
```

**Response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "New conversation session created successfully",
  "created_at": "2025-08-22T01:00:00"
}
```

**Frontend Integration Example:**
```javascript
async function createSession() {
  const response = await fetch('http://localhost:5001/create_session', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    }
  });
  const data = await response.json();
  return data.session_id;
}
```

---

### 3. Send Message
**`POST /process_message`**

Send a message to the chatbot and get a response.

**Request:**
```http
POST /process_message
Content-Type: application/json

{
  "message": "Hello, can you help me with trading?",
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Response:**
```json
{
  "response": "Hello! I'd be happy to help you with trading. What specific trading questions or topics would you like to discuss?",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "conversation_info": {
    "total_messages": 2,
    "total_chunks": 0,
    "current_messages_count": 2,
    "estimated_total_tokens": 156
  }
}
```

**Frontend Integration Example:**
```javascript
async function sendMessage(sessionId, message) {
  const response = await fetch('http://localhost:5001/process_message', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      message: message,
      session_id: sessionId
    })
  });
  const data = await response.json();
  return data.response;
}
```

---

### 4. Get Session Info
**`GET /session/{session_id}`**

Get information about a specific session.

**Response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "created_at": "2025-08-22T01:00:00",
  "last_activity": "2025-08-22T01:05:00",
  "total_messages": 8,
  "total_chunks": 1,
  "current_messages_count": 4,
  "estimated_total_tokens": 2456
}
```

---

### 5. Get Conversation History
**`GET /session/{session_id}/history`**

Get the full conversation history for a session.

**Response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "conversation_history": [
    {
      "role": "user",
      "content": "Hello!",
      "timestamp": "2025-08-22T01:00:00",
      "token_count": 8
    },
    {
      "role": "assistant",
      "content": "Hello! How can I help you today?",
      "timestamp": "2025-08-22T01:00:05",
      "token_count": 12
    }
  ],
  "chunks": [
    {
      "chunk_id": "chunk_1",
      "messages": [...],
      "total_tokens": 1500,
      "created_at": "2025-08-22T01:00:00",
      "summary": "Initial trading discussion about portfolio management"
    }
  ]
}
```

---

### 6. List All Sessions
**`GET /sessions`**

Get a list of all active sessions.

**Response:**
```json
{
  "sessions": [
    "550e8400-e29b-41d4-a716-446655440000",
    "550e8400-e29b-41d4-a716-446655440001"
  ],
  "total_sessions": 2
}
```

---

### 7. Delete Session
**`DELETE /session/{session_id}`**

Delete a specific session and all its data.

**Response:**
```json
{
  "message": "Session deleted successfully",
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

---

## 🔄 Complete Frontend Integration Example

Here's a complete example of how to integrate BrokerBot into your frontend:

```javascript
class BrokerBotAPI {
  constructor(baseUrl = 'http://localhost:5001') {
    this.baseUrl = baseUrl;
    this.sessionId = null;
  }

  async createSession() {
    try {
      const response = await fetch(`${this.baseUrl}/create_session`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      const data = await response.json();
      this.sessionId = data.session_id;
      return this.sessionId;
    } catch (error) {
      console.error('Failed to create session:', error);
      throw error;
    }
  }

  async sendMessage(message) {
    if (!this.sessionId) {
      throw new Error('No active session. Call createSession() first.');
    }

    try {
      const response = await fetch(`${this.baseUrl}/process_message`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: message,
          session_id: this.sessionId
        })
      });
      const data = await response.json();
      return data.response;
    } catch (error) {
      console.error('Failed to send message:', error);
      throw error;
    }
  }

  async getHistory() {
    if (!this.sessionId) return null;

    try {
      const response = await fetch(`${this.baseUrl}/session/${this.sessionId}/history`);
      return await response.json();
    } catch (error) {
      console.error('Failed to get history:', error);
      throw error;
    }
  }

  async checkHealth() {
    try {
      const response = await fetch(`${this.baseUrl}/health`);
      return await response.json();
    } catch (error) {
      console.error('Health check failed:', error);
      throw error;
    }
  }
}

// Usage Example:
const brokerBot = new BrokerBotAPI();

// Initialize and start chatting
async function startChat() {
  await brokerBot.createSession();
  const response = await brokerBot.sendMessage("Hello, I need help with trading!");
  console.log("Bot response:", response);
}
```

---

## 🚨 Error Handling

All endpoints return appropriate HTTP status codes:

- **200**: Success
- **201**: Created (for session creation)
- **400**: Bad Request (missing parameters)
- **404**: Not Found (invalid session ID)
- **500**: Internal Server Error

**Error Response Format:**
```json
{
  "error": "Error description",
  "details": "Additional error details if available"
}
```

---

## 🔒 Security Notes

1. **No Authentication**: Currently no authentication is required
2. **CORS Enabled**: All origins are allowed
3. **Session Management**: Sessions are identified by UUID only
4. **Data Persistence**: All conversations are stored in MySQL database

---

## 🏗️ Frontend Framework Examples

### React Example:
```jsx
import { useState, useEffect } from 'react';

function ChatBot() {
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');

  useEffect(() => {
    // Create session on component mount
    createSession();
  }, []);

  const createSession = async () => {
    const response = await fetch('http://localhost:5001/create_session', {
      method: 'POST'
    });
    const data = await response.json();
    setSessionId(data.session_id);
  };

  const sendMessage = async () => {
    if (!sessionId || !input.trim()) return;

    const userMessage = { role: 'user', content: input };
    setMessages(prev => [...prev, userMessage]);

    const response = await fetch('http://localhost:5001/process_message', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: input,
        session_id: sessionId
      })
    });
    const data = await response.json();

    const botMessage = { role: 'assistant', content: data.response };
    setMessages(prev => [...prev, botMessage]);
    setInput('');
  };

  return (
    <div>
      <div className="messages">
        {messages.map((msg, idx) => (
          <div key={idx} className={msg.role}>
            {msg.content}
          </div>
        ))}
      </div>
      <input
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
      />
      <button onClick={sendMessage}>Send</button>
    </div>
  );
}
```

### Vue.js Example:
```vue
<template>
  <div class="chatbot">
    <div class="messages">
      <div v-for="(message, index) in messages" :key="index" :class="message.role">
        {{ message.content }}
      </div>
    </div>
    <input v-model="input" @keyup.enter="sendMessage" placeholder="Type a message...">
    <button @click="sendMessage">Send</button>
  </div>
</template>

<script>
export default {
  data() {
    return {
      sessionId: null,
      messages: [],
      input: ''
    }
  },
  
  async mounted() {
    await this.createSession();
  },
  
  methods: {
    async createSession() {
      const response = await fetch('http://localhost:5001/create_session', {
        method: 'POST'
      });
      const data = await response.json();
      this.sessionId = data.session_id;
    },
    
    async sendMessage() {
      if (!this.sessionId || !this.input.trim()) return;
      
      this.messages.push({ role: 'user', content: this.input });
      
      const response = await fetch('http://localhost:5001/process_message', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: this.input,
          session_id: this.sessionId
        })
      });
      const data = await response.json();
      
      this.messages.push({ role: 'assistant', content: data.response });
      this.input = '';
    }
  }
}
</script>
```

---

This API is designed to be **frontend-agnostic** and can be integrated with any web framework, mobile app, or desktop application that can make HTTP requests. 