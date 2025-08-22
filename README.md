# Burdy's Auto Detail Chatbot API

A backend API for Burdy's Auto Detail chatbot with MySQL database integration and OpenAI assistant support.

## Features

- 🤖 OpenAI Assistant integration
- 🗄️ MySQL database storage for conversations
- 🔄 Session management
- 📊 Health check endpoints
- 🛡️ Error handling and validation

## Prerequisites

- Python 3.8+
- MySQL database
- OpenAI API key and Assistant ID

## Environment Variables

Create a `.env` file in the project root with the following variables:

```env
# OpenAI Configuration (REQUIRED)
OPENAI_API_KEY=your_openai_api_key_here

# MySQL Database Configuration (REQUIRED)
MYSQL_HOST=your_mysql_host
MYSQL_PORT=3306
MYSQL_DATABASE=your_database_name
MYSQL_USER=your_username
MYSQL_PASSWORD=your_password
MYSQL_SSL_MODE=REQUIRED
```

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up your environment variables in `.env` file

3. Ensure your MySQL database is running and accessible

## Running the API

### Development Mode
```bash
# Direct Python execution
python chat_api.py

# Using the production-ready launcher script
python start.py
```

### Production Mode (Railway)
```bash
# Use the Railway-friendly startup script
python start.py
```

The API will start on `http://localhost:5001` (development) or the Railway-assigned port (production)

## API Endpoints

### 1. Health Check
**Endpoint:** `GET /health`

**Description:** Returns comprehensive API status including database and OpenAI connectivity.

**Response:**
```json
{
  "status": "API is running",
  "timestamp": "2025-01-22T17:35:07.123456",
  "environment": "production",
  "database": "healthy",
  "openai": "healthy",
  "version": "1.0.0"
}
```

**Status Codes:**
- `200` - API is healthy
- `500` - Health check failed

---

### 2. Process Message
**Endpoint:** `POST /process_message`

**Description:** Processes a user message through OpenAI and stores the conversation in MySQL.

**Request Body:**
```json
{
  "message": "Hello, I need information about your auto detailing services",
  "session_id": "user_session_123"
}
```

**Parameters:**
- `message` (required): The user's message text
- `session_id` (optional): Unique session identifier for conversation tracking

**Response:**
```json
{
  "response": "Hello! I'd be happy to help you with our auto detailing services. We offer a range of services including...",
  "session_id": "user_session_123",
  "timestamp": "2025-01-22T17:35:07.123456"
}
```

**Status Codes:**
- `200` - Message processed successfully
- `400` - Missing or invalid message
- `500` - Server error (OpenAI or database issue)

---

### 3. Get Conversation History
**Endpoint:** `GET /conversation/{session_id}`

**Description:** Retrieves the complete conversation history for a specific session.

**URL Parameters:**
- `session_id` (required): The session identifier

**Response:**
```json
{
  "session_id": "user_session_123",
  "messages": [
    {
      "role": "user",
      "content": "Hello, I need information about your auto detailing services",
      "created_at": "2025-01-22T17:30:00.000000"
    },
    {
      "role": "assistant", 
      "content": "Hello! I'd be happy to help you with our auto detailing services...",
      "created_at": "2025-01-22T17:30:05.000000"
    }
  ]
}
```

**Status Codes:**
- `200` - Conversation history retrieved successfully
- `500` - Server error (database issue)

## API Usage Examples

### JavaScript/Fetch Examples

#### 1. Health Check
```javascript
const checkHealth = async () => {
  try {
    const response = await fetch('https://your-api.railway.app/health');
    const data = await response.json();
    console.log('API Status:', data);
  } catch (error) {
    console.error('Health check failed:', error);
  }
};
```

#### 2. Send a Message
```javascript
const sendMessage = async (message, sessionId = 'default_session') => {
  try {
    const response = await fetch('https://your-api.railway.app/process_message', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message: message,
        session_id: sessionId
      })
    });
    
    const data = await response.json();
    return data.response;
  } catch (error) {
    console.error('Failed to send message:', error);
    throw error;
  }
};

// Usage
sendMessage('Hello, I need car detailing services', 'user_123')
  .then(response => console.log('Bot response:', response));
```

#### 3. Get Conversation History
```javascript
const getConversationHistory = async (sessionId) => {
  try {
    const response = await fetch(`https://your-api.railway.app/conversation/${sessionId}`);
    const data = await response.json();
    return data.messages;
  } catch (error) {
    console.error('Failed to get conversation:', error);
    throw error;
  }
};
```

### cURL Examples

#### Local Testing
```bash
# Health Check
curl -X GET "http://localhost:5001/health"

# Send a Message
curl -X POST "http://localhost:5001/process_message" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello, I need auto detailing services",
    "session_id": "test_session"
  }'

# Get Conversation History
curl -X GET "http://localhost:5001/conversation/test_session"
```

#### Railway Production Testing
```bash
# Replace with your actual Railway URL
RAILWAY_URL="https://your-app-name.railway.app"

# Health Check
curl -X GET "${RAILWAY_URL}/health"

# Send a Message
curl -X POST "${RAILWAY_URL}/process_message" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What are your pricing options for full detail?",
    "session_id": "customer_456"
  }'

# Get Conversation History
curl -X GET "${RAILWAY_URL}/conversation/customer_456"
```

### Python Examples

#### Using requests library
```python
import requests
import json

# API base URL
API_BASE = "https://your-api.railway.app"

# Health check
def check_health():
    response = requests.get(f"{API_BASE}/health")
    return response.json()

# Send message
def send_message(message, session_id="default"):
    data = {
        "message": message,
        "session_id": session_id
    }
    response = requests.post(
        f"{API_BASE}/process_message",
        headers={"Content-Type": "application/json"},
        data=json.dumps(data)
    )
    return response.json()

# Get conversation history
def get_conversation(session_id):
    response = requests.get(f"{API_BASE}/conversation/{session_id}")
    return response.json()

# Usage example
if __name__ == "__main__":
    # Check API health
    health = check_health()
    print("API Health:", health)
    
    # Send a message
    response = send_message("Hello, I need car detailing services", "user_789")
    print("Bot Response:", response['response'])
    
    # Get conversation history
    history = get_conversation("user_789")
    print("Conversation History:", history)
```

### Testing Scripts
Run the provided test scripts:
```bash
# Local testing
./test_api.sh

# Railway testing (edit URL first)
./test_railway.sh
```

## Database Schema

The API automatically creates the following tables:

### conversations
- `id` (Primary Key)
- `session_id` (VARCHAR)
- `created_at` (TIMESTAMP)
- `updated_at` (TIMESTAMP)

### messages
- `id` (Primary Key)
- `conversation_id` (Foreign Key)
- `role` (ENUM: 'user', 'assistant')
- `content` (TEXT)
- `created_at` (TIMESTAMP)

## Error Handling

The API includes comprehensive error handling for:
- Missing environment variables
- Database connection failures
- OpenAI API errors
- Invalid input validation
- Network timeouts

## Development

- The API runs in debug mode by default
- CORS is enabled for cross-origin requests
- All database operations include proper error handling
- OpenAI integration includes retry logic and status checking

## Railway Deployment

### Environment Variables
Set these in your Railway project environment:

```env
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key

# MySQL Database Configuration
MYSQL_HOST=your_mysql_host
MYSQL_PORT=3306
MYSQL_DATABASE=your_database_name
MYSQL_USER=your_username
MYSQL_PASSWORD=your_password
MYSQL_SSL_MODE=REQUIRED

# Railway Environment (Optional)
RAILWAY_ENVIRONMENT=production
PORT=5001
HOST=0.0.0.0
FLASK_DEBUG=False
```

### Deployment Steps
1. Connect your GitHub repository to Railway
2. Set environment variables in Railway dashboard
3. Deploy - Railway will automatically use the Dockerfile
4. Test with the provided curl commands

### Railway-Specific Features
- Automatic port detection via `PORT` environment variable
- Production-optimized uvicorn settings
- Health check endpoint for monitoring
- CORS enabled for cross-origin requests

## Troubleshooting

1. **Database Connection Issues:**
   - Verify MySQL is running
   - Check environment variables
   - Ensure SSL mode is correct

2. **OpenAI Issues:**
   - Verify API key is valid
   - Check Assistant ID exists
   - Ensure sufficient API credits

3. **Port Conflicts:**
   - Change port in `chat_api.py` if 5001 is in use

4. **Railway Deployment Issues:**
   - Check Railway logs for error messages
   - Verify all environment variables are set
   - Ensure MySQL database is accessible from Railway 