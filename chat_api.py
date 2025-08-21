from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
from conversation_memory import ConversationMemory, FileStorage, InMemoryStorage
from config import Config
from llm_service import LLMService
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Validate configuration
config_errors = Config.validate_config()
if config_errors:
    print("❌ Configuration errors:")
    for error in config_errors:
        print(f"   • {error}")
    print("Please check your environment variables and .env file")
    exit(1)

# Print configuration
Config.print_config()

# Initialize conversation memory system
try:
    if Config.STORAGE_TYPE == 'file':
        storage = FileStorage(Config.STORAGE_DIR)
        print(f"📁 Using file-based conversation storage: {Config.STORAGE_DIR}")
    else:
        storage = InMemoryStorage()
        print("💾 Using in-memory conversation storage (data will not persist)")
except Exception as e:
    print(f"⚠️  File storage failed, falling back to in-memory: {e}")
    storage = InMemoryStorage()
    print("💾 Using in-memory conversation storage (data will not persist)")

# Initialize conversation memory with chunking
conversation_memory = ConversationMemory(
    storage=storage,
    max_tokens_per_chunk=Config.MAX_TOKENS_PER_CHUNK,
    max_context_tokens=Config.MAX_CONTEXT_TOKENS,
    session_timeout_hours=Config.SESSION_TIMEOUT_HOURS
)

# Initialize LLM service
try:
    llm_service = LLMService()
    print("🤖 LLM service initialized successfully")
    
    # Test OpenAI connection
    if llm_service.test_connection():
        print("✅ OpenAI connection test successful")
    else:
        print("⚠️  OpenAI connection test failed - check your API key")
except Exception as e:
    print(f"❌ Failed to initialize LLM service: {e}")
    llm_service = None

@app.route('/process_message', methods=['POST'])
def process_message():
    """
    Process a chat message with conversation memory
    
    Expected JSON payload:
    {
        "message": "User message text",
        "session_id": "optional_session_id"  # If not provided, returns error
    }
    
    Returns:
    {
        "response": "Bot response",
        "session_id": "session_identifier",
        "conversation_info": {
            "total_messages": 10,
            "total_chunks": 2,
            "current_messages_count": 3
        }
    }
    """
    try:
        data = request.json
        message = data.get('message')
        session_id = data.get('session_id')
        
        if not message:
            return jsonify({'error': 'Message is required'}), 400
        
        if not session_id:
            return jsonify({
                'error': 'Session ID is required. Use /create_session to create a new session.'
            }), 400
        
        # Verify session exists
        if not conversation_memory.storage.load_session(session_id):
            return jsonify({
                'error': f'Session {session_id} not found. Use /create_session to create a new session.'
            }), 404
        
        # Add user message to conversation
        success = conversation_memory.add_message(session_id, 'user', message)
        if not success:
            return jsonify({'error': 'Failed to save user message'}), 500
        
        # Get conversation context for LLM processing
        context = conversation_memory.get_conversation_context(session_id)
        
        # Generate response using LLM service
        if llm_service:
            try:
                response = llm_service.generate_response(context, message, session_id)
                logger.info(f"Generated LLM response for session {session_id}")
            except Exception as e:
                logger.error(f"LLM service error: {e}")
                response = f"I apologize, but I'm having trouble processing your message right now. Please try again."
        else:
            # Fallback response if LLM service is not available
            if len(context) > 2:
                response = f"I remember our conversation! You said: {message}. We've exchanged {len(context)} messages so far."
            else:
                response = f"Hello! You said: {message}"
        
        # Add assistant response to conversation
        conversation_memory.add_message(session_id, 'assistant', response)
        
        # Get session info for response
        session_info = conversation_memory.get_session_info(session_id)
        
        return jsonify({
            'response': response,
            'session_id': session_id,
            'conversation_info': {
                'total_messages': session_info.get('total_messages', 0),
                'total_chunks': session_info.get('total_chunks', 0),
                'current_messages_count': session_info.get('current_messages_count', 0),
                'estimated_total_tokens': session_info.get('estimated_total_tokens', 0)
            }
        }), 200
        
    except Exception as e:
        print(f"❌ Error processing message: {e}")
        return jsonify({'error': 'Failed to process message'}), 500

@app.route('/create_session', methods=['POST'])
def create_session():
    """
    Create a new conversation session
    
    Returns:
    {
        "session_id": "unique_session_identifier",
        "created_at": "2024-01-01T00:00:00"
    }
    """
    try:
        session_id = conversation_memory.create_session()
        session_info = conversation_memory.get_session_info(session_id)
        
        return jsonify({
            'session_id': session_id,
            'created_at': session_info.get('created_at'),
            'message': 'New conversation session created successfully'
        }), 201
        
    except Exception as e:
        print(f"❌ Error creating session: {e}")
        return jsonify({'error': 'Failed to create session'}), 500


@app.route('/session/<session_id>', methods=['GET'])
def get_session_info(session_id):
    """
    Get information about a conversation session
    
    Returns session statistics and metadata
    """
    try:
        session_info = conversation_memory.get_session_info(session_id)
        
        if not session_info:
            return jsonify({'error': 'Session not found'}), 404
        
        return jsonify(session_info), 200
        
    except Exception as e:
        print(f"❌ Error getting session info: {e}")
        return jsonify({'error': 'Failed to get session info'}), 500


@app.route('/session/<session_id>/history', methods=['GET'])
def get_conversation_history(session_id):
    """
    Get conversation history for a session
    
    Query parameters:
    - include_chunks: Number of recent chunks to include (default: 2)
    """
    try:
        include_chunks = int(request.args.get('include_chunks', 2))
        context = conversation_memory.get_conversation_context(session_id, include_chunks)
        
        if context is None:
            return jsonify({'error': 'Session not found'}), 404
        
        return jsonify({
            'session_id': session_id,
            'conversation_history': context,
            'total_messages': len(context)
        }), 200
        
    except Exception as e:
        print(f"❌ Error getting conversation history: {e}")
        return jsonify({'error': 'Failed to get conversation history'}), 500


@app.route('/session/<session_id>', methods=['DELETE'])
def delete_session(session_id):
    """Delete a conversation session"""
    try:
        success = conversation_memory.storage.delete_session(session_id)
        
        if success:
            return jsonify({'message': f'Session {session_id} deleted successfully'}), 200
        else:
            return jsonify({'error': 'Session not found'}), 404
            
    except Exception as e:
        print(f"❌ Error deleting session: {e}")
        return jsonify({'error': 'Failed to delete session'}), 500


@app.route('/sessions', methods=['GET'])
def list_sessions():
    """List all active sessions"""
    try:
        sessions = conversation_memory.storage.list_sessions()
        return jsonify({
            'sessions': sessions,
            'total_sessions': len(sessions)
        }), 200
        
    except Exception as e:
        print(f"❌ Error listing sessions: {e}")
        return jsonify({'error': 'Failed to list sessions'}), 500


@app.route('/cleanup_sessions', methods=['POST'])
def cleanup_expired_sessions():
    """Clean up expired sessions"""
    try:
        cleaned_count = conversation_memory.cleanup_expired_sessions()
        return jsonify({
            'message': f'Cleaned up {cleaned_count} expired sessions',
            'cleaned_sessions': cleaned_count
        }), 200
        
    except Exception as e:
        print(f"❌ Error cleaning up sessions: {e}")
        return jsonify({'error': 'Failed to cleanup sessions'}), 500


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint with memory system and LLM service status"""
    try:
        total_sessions = len(conversation_memory.storage.list_sessions())
        
        # Check LLM service status
        llm_status = "unavailable"
        llm_info = {}
        if llm_service:
            try:
                if llm_service.test_connection():
                    llm_status = "healthy"
                    llm_info = llm_service.get_usage_info()
                else:
                    llm_status = "connection_failed"
            except Exception as e:
                llm_status = f"error: {str(e)}"
        
        return jsonify({
            'status': 'API is running',
            'timestamp': datetime.now().isoformat(),
            'conversation_memory': {
                'storage_type': type(conversation_memory.storage).__name__,
                'total_sessions': total_sessions,
                'max_tokens_per_chunk': conversation_memory.max_tokens_per_chunk,
                'max_context_tokens': conversation_memory.max_context_tokens
            },
            'llm_service': {
                'status': llm_status,
                'info': llm_info
            }
        }), 200
    except Exception as e:
        logger.error(f"Error in health check: {e}")
        return jsonify({
            'status': 'API is running but some services may have issues',
            'timestamp': datetime.now().isoformat()
        }), 200

if __name__ == '__main__':
    print("🚀 Starting BrokerBot Chat API with Conversation Memory...")
    print("🌐 CORS enabled for API connections")
    print("🧠 Conversation memory with chunking enabled")
    print("🤖 LLM integration enabled")
    print("📝 Endpoints:")
    print("   • POST /create_session - Create new conversation")
    print("   • POST /process_message - Send message (requires session_id)")
    print("   • GET /session/<id> - Get session info")
    print("   • GET /session/<id>/history - Get conversation history")
    print("   • DELETE /session/<id> - Delete session")
    print("   • GET /sessions - List all sessions")
    print("   • POST /cleanup_sessions - Clean expired sessions")
    print("   • GET /health - Health check")
    print(f"🔗 Running on: http://{Config.HOST}:{Config.PORT}")
    app.run(debug=Config.DEBUG, host=Config.HOST, port=Config.PORT) 