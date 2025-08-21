# 🤖 BrokerBot

A trading assistant chatbot with conversation memory, built with Flask, OpenAI, and MySQL.

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Set Up Environment
Copy the example environment file and add your credentials:
```bash
cp env.example .env
```

Edit `.env` and add your OpenAI credentials:
```env
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_ASSISTANT_ID=your_openai_assistant_id_here
```

### 3. Run the Chatbot
```bash
python main.py
```

The server will start on `http://localhost:5001`

## 📋 Complete API Reference

### **Base URL**
- **Local**: `http://localhost:5001`
- **Production**: `https://your-app-name.railway.app` (after deployment)

### **Endpoints Overview**

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

---

### **1. Health Check**
```http
GET /health
```
**Response:**
```json
{
  "status": "API is running",
  "conversation_memory": {
    "storage_type": "MySQLStorage",
    "total_sessions": 0,
    "max_context_tokens": 4000,
    "max_tokens_per_chunk": 2000
  },
  "llm_service": {
    "status": "healthy",
    "info": {
      "assistant_id": "asst_xxxxx...",
      "model": "gpt-3.5-turbo"
    }
  }
}
```

### **2. Create Session** ⭐ **REQUIRED FIRST**
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

### **3. Send Message** ⭐ **MAIN ENDPOINT**
```http
POST /process_message
Content-Type: application/json

{
  "message": "Hello! Can you help me with trading advice?",
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```
**Response:**
```json
{
  "response": "Hello! I'd be happy to help you with trading advice...",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "conversation_info": {
    "total_messages": 2,
    "total_chunks": 0,
    "current_messages_count": 2,
    "estimated_total_tokens": 156
  }
}
```

### **4. Get Session Info**
```http
GET /session/{session_id}
```

### **5. Get Conversation History**
```http
GET /session/{session_id}/history
```

### **6. List All Sessions**
```http
GET /sessions
```

### **7. Delete Session**
```http
DELETE /session/{session_id}
```

---

## 💻 Frontend Integration

### **JavaScript Example:**
```javascript
class BrokerBotAPI {
  constructor() {
    this.baseUrl = 'https://your-app-name.railway.app'; // Update with your URL
    this.sessionId = null;
  }

  async createSession() {
    const response = await fetch(`${this.baseUrl}/create_session`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });
    const data = await response.json();
    this.sessionId = data.session_id;
    return this.sessionId;
  }

  async sendMessage(message) {
    if (!this.sessionId) {
      throw new Error('No active session. Call createSession() first.');
    }

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
  }
}

// Usage:
const bot = new BrokerBotAPI();
await bot.createSession();
const response = await bot.sendMessage("Hello!");
```

---

## 🧪 Testing the Chatbot

### **Quick Test Script:**
```bash
python quick_test.py
```

### **Manual Testing with curl:**
```bash
# 1. Create a session
curl -X POST http://localhost:5001/create_session

# 2. Send a message (replace SESSION_ID)
curl -X POST http://localhost:5001/process_message \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, can you help me with trading?", "session_id": "SESSION_ID"}'

# 3. Check health
curl http://localhost:5001/health
```

### **Browser Testing:**
1. Open `http://localhost:5001/health` to check if the server is running
2. Use Postman, Insomnia, or similar tools for full API testing

---

## 🔧 **Integration Notes**

- ✅ **CORS Enabled**: No cross-origin issues
- ❌ **No Authentication**: No API keys required
- ⏱️ **Response Times**: 3-15 seconds for message processing
- 🗄️ **Persistent Storage**: All conversations saved to MySQL
- 🔄 **Session Management**: Each user needs a unique session

## 🗄️ Database

The chatbot uses MySQL for conversation storage. Make sure your MySQL credentials are set in the `.env` file:

```env
MYSQL_HOST=your_mysql_host
MYSQL_PORT=3306
MYSQL_DATABASE=brokerbot
MYSQL_USER=your_username
MYSQL_PASSWORD=your_password
MYSQL_SSL_MODE=REQUIRED
```

## 📁 Project Structure

```
├── main.py                 # Main entry point
├── chat_api.py            # Flask API routes
├── llm_service.py         # OpenAI integration
├── conversation_memory.py # Conversation management
├── mysql_storage.py       # MySQL database storage
├── config.py              # Configuration settings
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables (create from env.example)
└── README.md             # This file
```

## 🔧 Configuration

Key settings in `config.py`:
- **Port**: 5001 (default)
- **Max Tokens**: 1000 per response
- **Memory**: 4000 tokens context limit
- **Storage**: MySQL database

## 🚀 Deployment

### Railway Deployment
```bash
railway up
```

### Docker Deployment
```bash
docker build -t brokerbot .
docker run -p 5001:5001 brokerbot
```

## 📝 License

This project is for educational purposes. 