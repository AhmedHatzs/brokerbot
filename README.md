# BrokerBot API

A Flask API for the BrokerBot chatbot service with intelligent conversation memory and chunking for long conversations.

## ✨ Features

- **🧠 Conversation Memory**: Persistent conversation history with intelligent chunking
- **📦 Smart Chunking**: Automatically chunks long conversations to stay within LLM token limits
- **💾 Flexible Storage**: File-based storage with in-memory fallback
- **🔄 Session Management**: Unique session IDs for tracking conversations
- **🧹 Auto Cleanup**: Automatic cleanup of expired sessions
- **🚀 Stateful Conversations**: LLM remembers context across multiple messages

## Recent Changes

- **Removed Frontend**: All frontend components (HTML, CSS, frontend server) have been completely removed
- **Renamed**: Changed from "Burdy's Auto Detail" to "BrokerBot"
- **Added Conversation Memory**: Implemented intelligent conversation memory with chunking
- **Session-Based**: Now uses session-based conversations instead of stateless requests

## Quick Start

### Local Development

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up environment variables:**
   ```bash
   # Copy the example environment file
   cp env.example .env
   
   # Edit .env and add your OpenAI credentials
   # OPENAI_API_KEY=your_actual_api_key_here
   # OPENAI_ASSISTANT_ID=your_actual_assistant_id_here
   ```

3. **Run the API server:**
   ```bash
   python run_api.py
   ```

4. **The API will be available at `http://localhost:5001`**

### Setting Up OpenAI Assistant

Before using BrokerBot, you need to create an OpenAI Assistant:

1. **Go to OpenAI Platform**: Visit https://platform.openai.com/assistants
2. **Create a new Assistant**:
   - Click "Create" 
   - Choose a name (e.g., "BrokerBot Assistant")
   - Add instructions for your bot's personality and behavior
   - Select a model (e.g., GPT-3.5-turbo or GPT-4)
   - Save the assistant
3. **Copy the Assistant ID**: The ID will be in the format `asst_xxxxxxxxxxxxxxxxxxxxx`
4. **Add to environment variables**: Set `OPENAI_ASSISTANT_ID` in your `.env` file

### Environment Variables

The following environment variables can be configured:

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `OPENAI_API_KEY` | Your OpenAI API key | - | ✅ Yes |
| `OPENAI_ASSISTANT_ID` | Your OpenAI Assistant ID | - | ✅ Yes |
| `OPENAI_MODEL` | OpenAI model to use | `gpt-3.5-turbo` | No |
| `OPENAI_MAX_TOKENS` | Max tokens per response | `1000` | No |
| `OPENAI_TEMPERATURE` | Response creativity (0-1) | `0.7` | No |
| `MAX_TOKENS_PER_CHUNK` | When to chunk conversations | `2000` | No |
| `MAX_CONTEXT_TOKENS` | Max context for LLM | `4000` | No |
| `SESSION_TIMEOUT_HOURS` | Session expiry time | `24` | No |
| `STORAGE_TYPE` | Storage type (`file`/`memory`) | `file` | No |
| `PORT` | Server port | `5001` | No |
| `DEBUG` | Debug mode | `False` | No |
| `BOT_NAME` | Bot name | `BrokerBot` | No |
| `BOT_PERSONALITY` | Bot personality prompt | See config | No |

### Testing the Conversation Memory

Run the included test script to see the conversation memory in action:

```bash
python test_conversation_memory.py
```

This will demonstrate:
- Creating a session
- Sending multiple messages
- Automatic chunking when token limits are reached
- Retrieving conversation history
- Testing memory with follow-up questions

### Basic Usage

1. **Create a new conversation session:**
   ```bash
   curl -X POST http://localhost:5001/create_session
   ```

2. **Send a message:**
   ```bash
   curl -X POST http://localhost:5001/process_message \
     -H "Content-Type: application/json" \
     -d '{"message": "Hello!", "session_id": "your-session-id"}'
   ```

### API Endpoints

#### Session Management
- **POST** `/create_session` - Create a new conversation session
- **GET** `/session/<id>` - Get session information and statistics
- **GET** `/session/<id>/history` - Get conversation history
- **DELETE** `/session/<id>` - Delete a session
- **GET** `/sessions` - List all active sessions
- **POST** `/cleanup_sessions` - Clean up expired sessions

#### Chat
- **POST** `/process_message` - Process chat messages (requires session_id)

#### System
- **GET** `/health` - Health check with memory system status

## 🧠 Conversation Memory System

### How It Works

The conversation memory system automatically manages long conversations by:

1. **Session Creation**: Each conversation gets a unique session ID
2. **Message Storage**: All messages are stored with timestamps and token counts
3. **Smart Chunking**: When conversations exceed token limits (default: 2000 tokens), older messages are moved to "chunks"
4. **Context Retrieval**: The system provides relevant conversation context to the LLM while staying within token limits
5. **Automatic Cleanup**: Expired sessions are automatically removed (default: 24 hours)

### Configuration

The memory system can be configured in `chat_api.py`:

```python
conversation_memory = ConversationMemory(
    storage=storage,
    max_tokens_per_chunk=2000,    # Chunk conversations every 2000 tokens
    max_context_tokens=4000,      # Maximum context for LLM
    session_timeout_hours=24      # Sessions expire after 24 hours
)
```

### Storage Options

- **File Storage** (Default): Persists conversations to `conversations/` directory
- **In-Memory Storage** (Fallback): For development or when file system isn't available

### Example Response

When you send a message, you'll receive conversation statistics:

```json
{
  "response": "I remember our conversation! You said: Hello again!",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "conversation_info": {
    "total_messages": 12,
    "total_chunks": 1,
    "current_messages_count": 4,
    "estimated_total_tokens": 2456
  }
}
```

### Deployment

#### Railway Deployment

1. **Set up Railway environment variables:**
   - Go to your Railway project settings
   - Add the following environment variables:
     - `OPENAI_API_KEY`: Your OpenAI API key
     - `OPENAI_ASSISTANT_ID`: Your OpenAI Assistant ID
     - `STORAGE_TYPE`: `file` (for persistent storage)
     - `DEBUG`: `False` (for production)

2. **Deploy:**
   ```bash
   railway up
   ```

3. **The API will be available at your Railway URL**

#### Docker Deployment

1. **Build the Docker image:**
   ```bash
   docker build -t brokerbot .
   ```

2. **Run with environment variables:**
   ```bash
   docker run -d \
     -p 5001:5001 \
     -e OPENAI_API_KEY=your_api_key \
     -e OPENAI_ASSISTANT_ID=your_assistant_id \
     -e STORAGE_TYPE=file \
     -e DEBUG=False \
     --name brokerbot \
     brokerbot
   ```

#### Environment Variables for Production

For production deployment, make sure to set:
- `OPENAI_API_KEY`: Your OpenAI API key
- `OPENAI_ASSISTANT_ID`: Your OpenAI Assistant ID
- `STORAGE_TYPE`: `file` (for persistent conversations)
- `DEBUG`: `False` (for security)
- `PORT`: `5001` (or your preferred port)

The project is configured for Railway deployment and will automatically use the API-only configuration with file-based conversation storage.

## Project Structure

- `chat_api.py` - Main Flask API server with conversation memory and LLM integration
- `conversation_memory.py` - Conversation memory system with chunking
- `llm_service.py` - OpenAI Assistant API integration service
- `config.py` - Environment variable configuration
- `run_api.py` - API launcher (production)
- `run_chatbot.py` - Legacy launcher (kept for reference)
- `run_with_uvicorn.py` - Legacy uvicorn launcher (kept for reference)
- `test_conversation_memory.py` - Test script for conversation memory
- `env.example` - Environment variables template
- `Dockerfile` - Docker configuration for API-only deployment
- `railway.toml` - Railway deployment configuration
- `conversations/` - Directory for stored conversation files (created automatically) 