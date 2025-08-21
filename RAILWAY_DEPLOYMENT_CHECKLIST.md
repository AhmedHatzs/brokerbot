# Railway Deployment Checklist for BrokerBot API

## ✅ Pre-Deployment Tests Completed

All API endpoints have been tested and are working correctly:

- ✅ Health Check (`GET /health`)
- ✅ Create Session (`POST /create_session`)
- ✅ Process Message (`POST /process_message`)
- ✅ Get Session Info (`GET /session/{id}`)
- ✅ Get Conversation History (`GET /session/{id}/history`)
- ✅ List All Sessions (`GET /sessions`)
- ✅ Error Handling (Invalid session, missing message)
- ✅ Conversation Memory with File Storage
- ✅ LLM Service Integration

## 🚀 Railway Deployment Configuration

### Files Ready for Deployment:

1. **Dockerfile** ✅
   - Uses Python 3.10-slim
   - Installs dependencies
   - Creates conversations directory
   - Exposes port 5001
   - Sets production environment variables

2. **railway.toml** ✅
   - Builds from Dockerfile
   - Starts with `python run_api.py`
   - Internal port 5001
   - TCP protocol

3. **requirements.txt** ✅
   - All dependencies listed
   - Version pinned for stability

4. **Environment Variables** ✅
   - `.env` file with all required variables
   - Railway will use these as environment variables

## 🔧 Required Environment Variables for Railway

Make sure these are set in Railway dashboard:

```bash
# Required
OPENAI_API_KEY=your_actual_openai_api_key
OPENAI_ASSISTANT_ID=your_actual_assistant_id

# Optional (have defaults)
OPENAI_MODEL=gpt-3.5-turbo
OPENAI_MAX_TOKENS=1000
OPENAI_TEMPERATURE=0.7
MAX_TOKENS_PER_CHUNK=2000
MAX_CONTEXT_TOKENS=4000
SESSION_TIMEOUT_HOURS=24
STORAGE_TYPE=file
STORAGE_DIR=conversations
PORT=5001
HOST=0.0.0.0
DEBUG=False
BOT_NAME=BrokerBot
BOT_PERSONALITY=You are a helpful AI assistant named BrokerBot...
```

## 📋 Deployment Steps

1. **Push to GitHub** (if not already done)
   ```bash
   git add .
   git commit -m "Ready for Railway deployment"
   git push origin main
   ```

2. **Connect to Railway**
   - Go to Railway dashboard
   - Create new project
   - Connect GitHub repository
   - Select this repository

3. **Set Environment Variables**
   - Add all required environment variables in Railway dashboard
   - Use your actual OpenAI API key and Assistant ID

4. **Deploy**
   - Railway will automatically build and deploy
   - Monitor the build logs for any issues

5. **Test Deployed API**
   ```bash
   # Replace with your Railway URL
   curl -X GET https://your-app.railway.app/health
   ```

## 🧪 Post-Deployment Testing

After deployment, test these endpoints:

```bash
# Health check
curl -X GET https://your-app.railway.app/health

# Create session
curl -X POST https://your-app.railway.app/create_session

# Send message (use session ID from above)
curl -X POST https://your-app.railway.app/process_message \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello!", "session_id": "SESSION_ID_HERE"}'
```

## 🔍 Monitoring

- Check Railway logs for any errors
- Monitor API response times
- Verify conversation memory persistence
- Test LLM service connectivity

## 🚨 Troubleshooting

### Common Issues:

1. **Build fails**: Check requirements.txt and Dockerfile
2. **API key errors**: Verify environment variables in Railway
3. **Port issues**: Ensure internal port is 5001
4. **Storage issues**: Check if conversations directory is created

### Debug Commands:

```bash
# Check Railway logs
railway logs

# Check environment variables
railway variables

# Restart deployment
railway up
```

## ✅ Ready for Deployment!

Your BrokerBot API is fully tested and ready for Railway deployment. All endpoints are working correctly, error handling is in place, and the configuration is optimized for production. 