#!/usr/bin/env python3
"""
Burdy's Auto Detail Chatbot API
Backend API with MySQL and OpenAI integration
"""

import os
import mysql.connector
from mysql.connector import Error
import openai
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Production-ready CORS configuration
if os.getenv('RAILWAY_ENVIRONMENT') == 'production':
    # In production, configure CORS for specific origins
    CORS(app, origins=[
        'https://your-frontend-domain.com',  # Replace with your actual frontend domain
        'http://localhost:3000',  # For local development
        'http://localhost:5173'   # For Vite dev server
    ])
else:
    # In development, allow all origins
    CORS(app)

# OpenAI Configuration
from openai import OpenAI
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# MySQL Configuration
MYSQL_CONFIG = {
    'host': os.getenv('MYSQL_HOST'),
    'port': int(os.getenv('MYSQL_PORT', 3306)),
    'database': os.getenv('MYSQL_DATABASE'),
    'user': os.getenv('MYSQL_USER'),
    'password': os.getenv('MYSQL_PASSWORD'),
    'ssl_disabled': os.getenv('MYSQL_SSL_MODE', 'REQUIRED') != 'REQUIRED'
}

def get_mysql_connection():
    """Create and return MySQL connection with production-ready error handling"""
    try:
        connection = mysql.connector.connect(**MYSQL_CONFIG)
        return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        # In production, log more details but don't expose sensitive info
        if os.getenv('RAILWAY_ENVIRONMENT') == 'production':
            print(f"Database connection failed - Host: {MYSQL_CONFIG.get('host')}, Database: {MYSQL_CONFIG.get('database')}")
        return None
    except Exception as e:
        print(f"Unexpected error connecting to MySQL: {e}")
        return None

def init_database():
    """Initialize database tables if they don't exist"""
    connection = get_mysql_connection()
    if not connection:
        return False
    
    try:
        cursor = connection.cursor()
        
        # Create conversations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INT AUTO_INCREMENT PRIMARY KEY,
                session_id VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
        """)
        
        # Create messages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INT AUTO_INCREMENT PRIMARY KEY,
                conversation_id INT,
                role ENUM('user', 'assistant') NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
            )
        """)
        
        connection.commit()
        cursor.close()
        connection.close()
        return True
        
    except Error as e:
        print(f"Error initializing database: {e}")
        return False

def save_message_to_db(session_id, role, content):
    """Save message to MySQL database"""
    connection = get_mysql_connection()
    if not connection:
        return None
    
    try:
        cursor = connection.cursor()
        
        # Get or create conversation
        cursor.execute("SELECT id FROM conversations WHERE session_id = %s", (session_id,))
        result = cursor.fetchone()
        
        if result:
            conversation_id = result[0]
        else:
            cursor.execute("INSERT INTO conversations (session_id) VALUES (%s)", (session_id,))
            conversation_id = cursor.lastrowid
        
        # Save message
        cursor.execute(
            "INSERT INTO messages (conversation_id, role, content) VALUES (%s, %s, %s)",
            (conversation_id, role, content)
        )
        
        connection.commit()
        cursor.close()
        connection.close()
        return conversation_id
        
    except Error as e:
        print(f"Error saving message to database: {e}")
        return None

def get_conversation_history(session_id):
    """Get conversation history from database"""
    connection = get_mysql_connection()
    if not connection:
        return []
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT m.role, m.content, m.created_at 
            FROM messages m 
            JOIN conversations c ON m.conversation_id = c.id 
            WHERE c.session_id = %s 
            ORDER BY m.created_at ASC
        """, (session_id,))
        
        messages = cursor.fetchall()
        cursor.close()
        connection.close()
        return messages
        
    except Error as e:
        print(f"Error getting conversation history: {e}")
        return []

@app.route('/', methods=['GET'])
def root():
    """Simple root endpoint for basic connectivity testing"""
    return jsonify({
        'message': "Burdy's Auto Detail Chatbot API is running",
        'status': 'ok',
        'timestamp': datetime.now().isoformat()
    }), 200

@app.route('/process_message', methods=['POST'])
def process_message():
    """Process chat message with OpenAI and save to MySQL"""
    try:
        data = request.json
        message = data.get('message')
        session_id = data.get('session_id', 'default_session')
        
        if not message:
            return jsonify({'error': 'Message is required'}), 400
        
        # Save user message to database (optional)
        try:
            save_message_to_db(session_id, 'user', message)
            # Get conversation history for context
            history = get_conversation_history(session_id)
        except Exception as e:
            print(f"Database operation failed: {e}")
            history = []
        
        # Use OpenAI Chat Completions API
        try:
            # Prepare conversation context
            messages = [{"role": "system", "content": "You are Burdy's Auto Detail assistant. Help customers with car detailing services, pricing, and scheduling."}]
            
            # Add conversation history if available
            if history:
                for msg in history[-10:]:  # Limit to last 10 messages for context
                    messages.append({"role": msg['role'], "content": msg['content']})
            
            # Add current user message
            messages.append({"role": "user", "content": message})
            
            # Get response from OpenAI
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                max_tokens=500,
                temperature=0.7
            )
            assistant_response = response.choices[0].message.content
        except Exception as e:
            print(f"OpenAI API error: {e}")
            return jsonify({'error': 'Failed to get response from OpenAI'}), 500
        
        # Save assistant response to database (optional)
        try:
            save_message_to_db(session_id, 'assistant', assistant_response)
        except Exception as e:
            print(f"Failed to save assistant response to database: {e}")
        
        return jsonify({
            'response': assistant_response,
            'session_id': session_id,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        print(f"Error processing message: {e}")
        return jsonify({'error': 'Failed to process message'}), 500

@app.route('/health', methods=['GET'])
def health():
    """Production-ready health check endpoint optimized for Railway"""
    try:
        # Check database connectivity (fast check)
        db_status = "healthy"
        try:
            connection = get_mysql_connection()
            if connection:
                # Simple ping test
                cursor = connection.cursor()
                cursor.execute("SELECT 1")
                cursor.fetchone()
                cursor.close()
                connection.close()
            else:
                db_status = "unhealthy"
        except Exception as e:
            print(f"Database health check failed: {e}")
            db_status = "unhealthy"
        
        # Check OpenAI API connectivity (minimal test)
        openai_status = "healthy"
        try:
            # Very minimal test call to OpenAI
            test_response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=1,
                temperature=0
            )
        except Exception as e:
            print(f"OpenAI health check failed: {e}")
            openai_status = "unhealthy"
        
        return jsonify({
            'status': 'API is running',
            'timestamp': datetime.now().isoformat(),
            'environment': os.getenv('RAILWAY_ENVIRONMENT', 'development'),
            'database': db_status,
            'openai': openai_status,
            'version': '1.0.0'
        }), 200
    except Exception as e:
        print(f"Health check error: {e}")
        return jsonify({'error': 'Health check failed'}), 500

@app.route('/conversation/<session_id>', methods=['GET'])
def get_conversation(session_id):
    """Get conversation history for a session"""
    try:
        messages = get_conversation_history(session_id)
        return jsonify({
            'session_id': session_id,
            'messages': messages
        }), 200
    except Exception as e:
        return jsonify({'error': 'Failed to get conversation'}), 500

if __name__ == '__main__':
    print("🚀 Starting Burdy's Auto Detail Chat API...")
    print("🔧 Initializing database...")
    
    try:
        if init_database():
            print("✅ Database initialized successfully")
        else:
            print("⚠️  Database initialization failed - API will continue without database")
    except Exception as e:
        print(f"⚠️  Database initialization error: {e} - API will continue without database")
    
    print("🌐 CORS enabled for API access")
    print("💬 Endpoint: /process_message")
    
    # Get port from Railway environment or use default
    port = int(os.getenv('PORT', 5007))
    host = os.getenv('HOST', '0.0.0.0')
    
    print(f"🔗 Running on: http://{host}:{port}")
    print(f"📊 Health check: http://{host}:{port}/health")
    
    # Production-ready configuration
    is_production = os.getenv('RAILWAY_ENVIRONMENT') == 'production'
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() == 'true' and not is_production
    
    if is_production:
        print("🚀 Running in PRODUCTION mode")
        # In production, use threaded mode for better performance
        app.run(debug=False, host=host, port=port, threaded=True)
    else:
        print("🔧 Running in DEVELOPMENT mode")
        app.run(debug=debug_mode, host=host, port=port) 