# 🧪 Postman Testing Guide for BrokerBot

This guide shows you how to test your BrokerBot chatbot using Postman, both locally and after deployment.

## 📋 **Prerequisites**

1. **Download Postman**: https://www.postman.com/downloads/
2. **Local Testing**: Your chatbot running on `http://localhost:5001`
3. **Deployed Testing**: Your chatbot deployed to Railway/Heroku/etc.

---

## 🏠 **Local Testing (Before Deployment)**

### **Step 1: Start Your Chatbot Locally**
```bash
python main.py
```

### **Step 2: Import Postman Collection**

Create a new collection in Postman called "BrokerBot Local Testing" and add these requests:

---

## 📝 **Postman Collection Setup**

### **1. Health Check**
- **Method**: `GET`
- **URL**: `http://localhost:5001/health`
- **Description**: Check if the API is running

**Expected Response:**
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
      "model": "gpt-3.5-turbo",
      "max_tokens": 1000,
      "temperature": 0.7
    }
  },
  "timestamp": "2025-08-22T01:00:00.000000"
}
```

### **2. Create Session**
- **Method**: `POST`
- **URL**: `http://localhost:5001/create_session`
- **Headers**: 
  - `Content-Type: application/json`
- **Body**: None (empty)

**Expected Response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "New conversation session created successfully",
  "created_at": "2025-08-22T01:00:00"
}
```

### **3. Send Message**
- **Method**: `POST`
- **URL**: `http://localhost:5001/process_message`
- **Headers**: 
  - `Content-Type: application/json`
- **Body** (raw JSON):
```json
{
  "message": "Hello! Can you help me with trading advice?",
  "session_id": "{{session_id}}"
}
```

**Expected Response:**
```json
{
  "response": "Hello! I'd be happy to help you with trading advice. What specific questions do you have about trading?",
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
- **Method**: `GET`
- **URL**: `http://localhost:5001/session/{{session_id}}`

### **5. Get Conversation History**
- **Method**: `GET`
- **URL**: `http://localhost:5001/session/{{session_id}}/history`

### **6. List All Sessions**
- **Method**: `GET`
- **URL**: `http://localhost:5001/sessions`

### **7. Delete Session**
- **Method**: `DELETE`
- **URL**: `http://localhost:5001/session/{{session_id}}`

---

## 🚀 **Deployed Testing (After Deployment)**

### **Step 1: Deploy to Railway**
```bash
railway up
```

### **Step 2: Get Your Deployed URL**
After deployment, Railway will give you a URL like:
`https://your-app-name.railway.app`

### **Step 3: Create New Postman Collection**
Create a new collection called "BrokerBot Deployed" and use the same requests but with your deployed URL:

**Base URL**: `https://your-app-name.railway.app`

---

## 🔄 **Testing Workflow**

### **Complete Chat Flow Test:**

1. **Health Check** → Verify API is running
2. **Create Session** → Get session ID
3. **Send Message 1** → "Hello, I'm new to trading"
4. **Send Message 2** → "What should I know about risk management?"
5. **Send Message 3** → "Can you explain technical analysis?"
6. **Get History** → Verify conversation is saved
7. **Get Session Info** → Check message count
8. **Delete Session** → Clean up

### **Error Testing:**

1. **Send message without session_id** → Should return 400 error
2. **Use invalid session_id** → Should return 404 error
3. **Send empty message** → Should handle gracefully

---

## 📊 **Postman Environment Variables**

Create a Postman environment with these variables:

| Variable | Local Value | Deployed Value |
|----------|-------------|----------------|
| `base_url` | `http://localhost:5001` | `https://your-app-name.railway.app` |
| `session_id` | (empty - will be set by Create Session) | (empty - will be set by Create Session) |

### **Setting up Environment Variables:**

1. **Create Environment**: Click the gear icon → "Add"
2. **Add Variables**: 
   - `base_url`: `http://localhost:5001`
   - `session_id`: (leave empty)
3. **Use in URLs**: `{{base_url}}/health`

### **Auto-setting session_id:**

In the "Create Session" request, add this test script:
```javascript
pm.test("Session created", function () {
    var jsonData = pm.response.json();
    pm.environment.set("session_id", jsonData.session_id);
});
```

---

## 🧪 **Automated Testing Scripts**

### **Health Check Test Script:**
```javascript
pm.test("Status code is 200", function () {
    pm.response.to.have.status(200);
});

pm.test("API is running", function () {
    var jsonData = pm.response.json();
    pm.expect(jsonData.status).to.eql("API is running");
});

pm.test("LLM service is healthy", function () {
    var jsonData = pm.response.json();
    pm.expect(jsonData.llm_service.status).to.eql("healthy");
});
```

### **Create Session Test Script:**
```javascript
pm.test("Status code is 201", function () {
    pm.response.to.have.status(201);
});

pm.test("Session ID is generated", function () {
    var jsonData = pm.response.json();
    pm.expect(jsonData.session_id).to.not.be.empty;
    pm.environment.set("session_id", jsonData.session_id);
});
```

### **Send Message Test Script:**
```javascript
pm.test("Status code is 200", function () {
    pm.response.to.have.status(200);
});

pm.test("Response is generated", function () {
    var jsonData = pm.response.json();
    pm.expect(jsonData.response).to.not.be.empty;
    pm.expect(jsonData.response.length).to.be.greaterThan(10);
});
```

---

## 🔍 **Testing Checklist**

### **Before Deployment:**
- [ ] Health check returns 200
- [ ] LLM service status is "healthy"
- [ ] Can create session
- [ ] Can send message and get response
- [ ] Conversation history is saved
- [ ] Session info shows correct message count
- [ ] Can delete session

### **After Deployment:**
- [ ] All local tests pass with deployed URL
- [ ] CORS is working (no CORS errors)
- [ ] Response times are acceptable
- [ ] Database connection works
- [ ] OpenAI integration works

---

## 🚨 **Common Issues & Solutions**

### **CORS Errors:**
- **Issue**: Frontend can't connect to API
- **Solution**: CORS is already enabled in the code

### **Session Not Found:**
- **Issue**: 404 error when using session_id
- **Solution**: Make sure to create session first

### **Database Connection Failed:**
- **Issue**: MySQL connection errors
- **Solution**: Check environment variables in deployment

### **OpenAI Authentication Failed:**
- **Issue**: LLM service status shows "connection_failed"
- **Solution**: Verify OPENAI_API_KEY and OPENAI_ASSISTANT_ID

---

## 📱 **Mobile Testing**

You can also test your deployed API using:

### **iOS Shortcuts:**
1. Create a new shortcut
2. Add "Get Contents of URL" action
3. Use your deployed URL + endpoint
4. Test the response

### **Android Apps:**
- **API Tester**: Simple API testing app
- **Postman Mobile**: Full Postman experience

---

## 🎯 **Performance Testing**

### **Load Testing with Postman:**
1. **Runner**: Use Postman's Collection Runner
2. **Iterations**: Set to 10-50 iterations
3. **Delay**: 1000ms between requests
4. **Monitor**: Response times and success rates

### **Expected Performance:**
- **Response Time**: < 5 seconds for message processing
- **Success Rate**: > 95%
- **Concurrent Users**: Test with 5-10 simultaneous requests

---

## 📈 **Monitoring After Deployment**

### **Key Metrics to Monitor:**
1. **Response Times**: Should be consistent
2. **Error Rates**: Should be < 5%
3. **Database Performance**: Session creation/retrieval
4. **OpenAI API Usage**: Token consumption and costs

### **Health Check Monitoring:**
Set up automated health checks to your deployed URL:
```bash
curl https://your-app-name.railway.app/health
```

---

This testing guide ensures your chatbot works perfectly both locally and in production! 🚀 