# 🚗 Burdy's Auto Detail Chatbot API

A production-ready backend API for Burdy's Auto Detail chatbot with MySQL database integration and OpenAI assistant support. Built with Flask and optimized for Railway deployment.

## ✨ Features

- **AI-Powered Chatbot**: OpenAI GPT-3.5-turbo integration for intelligent responses
- **Conversation History**: Persistent chat sessions with MySQL database
- **Production Ready**: Optimized for Railway deployment with Docker
- **Health Monitoring**: Comprehensive health checks and status endpoints
- **CORS Support**: Cross-origin resource sharing for frontend integration
- **Error Handling**: Robust error handling and logging
- **Security**: Non-root Docker container and environment variable protection

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- MySQL database
- OpenAI API key

### Local Development

1. **Clone the repository:**
   ```bash
   git clone <your-repo-url>
   cd brokerbot
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables:**
   Create a `.env` file:
   ```bash
   # OpenAI Configuration
   OPENAI_API_KEY=your_openai_api_key_here
   OPENAI_ASSISTANT_ID=your_openai_assistant_id_here
   
   # MySQL Database Configuration
   MYSQL_HOST=localhost
   MYSQL_PORT=3306
   MYSQL_DATABASE=burdy_chatbot
   MYSQL_USER=root
   MYSQL_PASSWORD=
   
   # Development Configuration
   RAILWAY_ENVIRONMENT=development
   PORT=5007
   ```

4. **Start the API:**
   ```bash
   python start.py
   ```

5. **Test the API:**
   ```bash
   # Health check
   curl http://localhost:5007/health
   
   # Chat endpoint
   curl -X POST http://localhost:5007/process_message \
     -H "Content-Type: application/json" \
     -d '{"message": "Hello, can you help me with car detailing?", "session_id": "test-session"}'
   ```

## 🌐 API Endpoints

### Root Endpoint
- **GET** `/` - Basic connectivity test
- **Response:** API status and timestamp

### Health Check
- **GET** `/health` - Comprehensive health status
- **Response:** Database, OpenAI, and environment status

### Chat Processing
- **POST** `/process_message` - Process chat messages
- **Body:** `{"message": "user message", "session_id": "unique-session-id"}`
- **Response:** AI-generated response with session tracking

### Conversation History
- **GET** `/conversation/<session_id>` - Get conversation history
- **Response:** All messages for the specified session

## 🚀 Railway Deployment

### 1. Connect to Railway

1. Go to [Railway Dashboard](https://railway.app/dashboard)
2. Click "New Project" → "Deploy from GitHub repo"
3. Connect your GitHub account and select this repository

### 2. Environment Variables

Set these in your Railway project settings:

```bash
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_ASSISTANT_ID=your_openai_assistant_id_here

# MySQL Database Configuration
MYSQL_HOST=your_mysql_host
MYSQL_PORT=3306
MYSQL_DATABASE=your_database_name
MYSQL_USER=your_database_user
MYSQL_PASSWORD=your_database_password
MYSQL_SSL_MODE=REQUIRED

# Railway Configuration
RAILWAY_ENVIRONMENT=production
PORT=5007
```

### 3. Deploy

Railway will automatically:
- Build your Docker container
- Set the PORT environment variable
- Deploy your application
- Provide a public URL

### 4. Test Deployment

```bash
# Test root endpoint
curl https://your-app-name.railway.app/

# Test health check
curl https://your-app-name.railway.app/health

# Test chat functionality
curl -X POST https://your-app-name.railway.app/process_message \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello", "session_id": "test"}'
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `OPENAI_API_KEY` | OpenAI API key for AI responses | Yes | - |
| `OPENAI_ASSISTANT_ID` | OpenAI Assistant ID for conversations | Yes | - |
| `MYSQL_HOST` | MySQL database host | Yes | localhost |
| `MYSQL_PORT` | MySQL database port | No | 3306 |
| `MYSQL_DATABASE` | MySQL database name | Yes | burdy_chatbot |
| `MYSQL_USER` | MySQL database user | Yes | root |
| `MYSQL_PASSWORD` | MySQL database password | Yes | - |
| `MYSQL_SSL_MODE` | MySQL SSL mode | No | REQUIRED |
| `RAILWAY_ENVIRONMENT` | Environment mode | No | development |
| `PORT` | Application port | No | 5007 |
| `HOST` | Application host | No | 0.0.0.0 |

### Database Schema

The application automatically creates these tables:

```sql
-- Conversations table
CREATE TABLE conversations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Messages table
CREATE TABLE messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    conversation_id INT,
    role ENUM('user', 'assistant') NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
);
```

## 🏗️ Architecture

### File Structure

```
brokerbot/
├── chat_api.py          # Main Flask application
├── start.py             # Production/development startup script
├── requirements.txt     # Python dependencies
├── Dockerfile          # Production Docker configuration
├── railway.toml        # Railway deployment configuration
├── healthcheck.sh      # Health check script
├── .dockerignore       # Docker ignore file
└── README.md           # This file
```

### Key Components

- **Flask Application** (`chat_api.py`): Main API with endpoints and business logic
- **Startup Script** (`start.py`): Handles development vs production modes
- **Docker Configuration**: Production-ready container setup
- **Railway Configuration**: Optimized for Railway deployment

## 🔍 Monitoring & Health Checks

### Health Endpoint Response

```json
{
  "status": "API is running",
  "timestamp": "2025-01-22T13:15:09.123456",
  "environment": "production",
  "database": "healthy",
  "openai": "healthy",
  "version": "1.0.0"
}
```

### Railway Health Checks

- **Path:** `/health`
- **Timeout:** 10 seconds
- **Interval:** 30 seconds
- **Retries:** 5 attempts

## 🛠️ Development

### Running Tests

```bash
# Test health endpoint
curl http://localhost:5007/health

# Test chat functionality
curl -X POST http://localhost:5007/process_message \
  -H "Content-Type: application/json" \
  -d '{"message": "Test message", "session_id": "test"}'
```

### Development Mode

The application automatically detects development mode and:
- Uses Flask's built-in development server
- Enables debug mode
- Allows all CORS origins
- Uses local MySQL configuration

### Production Mode

Production mode (Railway) uses:
- Gunicorn WSGI server
- Single worker configuration
- Railway-optimized settings
- Production CORS configuration

## 🔒 Security Features

- **Non-root Docker container** for enhanced security
- **Environment variable protection** for sensitive data
- **CORS configuration** for production environments
- **Input validation** and error handling
- **Database connection timeouts** to prevent hanging

## 📊 Performance Optimizations

- **Single gunicorn worker** for Railway resource constraints
- **Database connection pooling** for efficient MySQL connections
- **Conversation history limiting** (last 10 messages for context)
- **Railway-optimized timeouts** and health checks
- **Preloaded application** for faster startup

## 🚨 Troubleshooting

### Common Issues

1. **Database Connection Errors**
   - Verify MySQL credentials and host
   - Check SSL mode configuration
   - Ensure database is accessible

2. **OpenAI API Errors**
   - Verify API key is valid
   - Check API quota and permissions
   - Ensure API key has sufficient credits

3. **Port Configuration**
   - Application uses port 5007 by default
   - Railway automatically sets PORT environment variable
   - Health checks use Railway's PORT

4. **Deployment Issues**
   - Check Railway build logs
   - Verify all environment variables are set
   - Test endpoints individually

### Logs and Debugging

- **Railway logs:** `railway logs`
- **Application logs:** Check Railway dashboard
- **Health endpoint:** Provides detailed status information

## 📈 Scaling Considerations

- Monitor Railway usage and billing
- Consider upgrading Railway plan for higher traffic
- Optimize database queries for performance
- Review OpenAI API usage and costs

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## 📞 Support

For issues and questions:
1. Check the troubleshooting section
2. Review Railway documentation
3. Test endpoints individually
4. Verify environment configuration

---

**Last Updated:** August 22, 2025  
**Version:** 1.0.0  
**Status:** Production Ready ✅ 