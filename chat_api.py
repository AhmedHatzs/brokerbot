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
import uuid

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
assistant_id = os.getenv('OPENAI_ASSISTANT_ID')

# MySQL Configuration
def get_mysql_config():
    """Get MySQL configuration based on environment"""
    is_production = os.getenv('RAILWAY_ENVIRONMENT') == 'production'
    
    if is_production:
        # Production configuration (Railway with Aiven Cloud MySQL)
        config = {
            'host': os.getenv('MYSQL_HOST'),
            'port': int(os.getenv('MYSQL_PORT', 3306)),
            'database': os.getenv('MYSQL_DATABASE'),
            'user': os.getenv('MYSQL_USER'),
            'password': os.getenv('MYSQL_PASSWORD'),
            'connect_timeout': 30,  # Increased timeout for cloud connections
            'autocommit': True,
            'charset': 'utf8mb4',
            'collation': 'utf8mb4_unicode_ci'
        }
        
        # Handle SSL configuration for Aiven Cloud
        ssl_mode = os.getenv('MYSQL_SSL_MODE', 'REQUIRED')
        if ssl_mode == 'REQUIRED':
            config['ssl_ca'] = None  # Use system CA certificates
            config['ssl_verify_cert'] = True
        elif ssl_mode == 'DISABLED':
            config['ssl_disabled'] = True
        else:
            # Default to SSL enabled
            config['ssl_ca'] = None
            config['ssl_verify_cert'] = True
            
        return config
    else:
        # Development configuration (Local MySQL)
        return {
            'host': 'localhost',
            'port': 3306,
            'database': 'burdy_chatbot',
            'user': 'root',
            'password': '',
            'ssl_disabled': True,
            'connect_timeout': 10,
            'autocommit': True
        }

MYSQL_CONFIG = get_mysql_config()

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
        
        # Create conversations table with thread_id support
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INT AUTO_INCREMENT PRIMARY KEY,
                thread_id VARCHAR(255) UNIQUE NOT NULL,
                session_id VARCHAR(255) NOT NULL,
                title VARCHAR(500) DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_thread_id (thread_id),
                INDEX idx_session_id (session_id)
            )
        """)
        
        # Create messages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INT AUTO_INCREMENT PRIMARY KEY,
                conversation_id INT,
                thread_id VARCHAR(255) NOT NULL,
                role ENUM('user', 'assistant') NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
                INDEX idx_thread_id (thread_id),
                INDEX idx_conversation_id (conversation_id)
            )
        """)
        
        connection.commit()
        cursor.close()
        connection.close()
        return True
        
    except Error as e:
        print(f"Error initializing database: {e}")
        return False

# Initialize database when app is created (for gunicorn compatibility)
print("🔧 Initializing database...")
import threading
import time

def init_db_background():
    """Initialize database in background thread with retry logic"""
    max_retries = 3
    retry_delay = 5  # seconds
    
    for attempt in range(max_retries):
        try:
            print(f"🔄 Database initialization attempt {attempt + 1}/{max_retries}")
            if init_database():
                print("✅ Database initialized successfully")
                return
            else:
                print(f"⚠️  Database initialization failed (attempt {attempt + 1})")
        except Exception as e:
            print(f"⚠️  Database initialization error (attempt {attempt + 1}): {e}")
        
        if attempt < max_retries - 1:
            print(f"⏳ Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)
    
    print("❌ Database initialization failed after all attempts - API will continue without database")
    print("💡 Check your MySQL environment variables and connection settings")

# Start database initialization in background thread
db_thread = threading.Thread(target=init_db_background, daemon=True)
db_thread.start()

def generate_thread_id():
    """Generate a unique thread ID for conversations"""
    return str(uuid.uuid4())

def get_or_create_thread(session_id, thread_id=None):
    """Get existing thread or create a new one"""
    connection = get_mysql_connection()
    if not connection:
        return None
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        if thread_id:
            # Try to get existing thread
            cursor.execute("""
                SELECT id, thread_id, session_id, title, created_at 
                FROM conversations 
                WHERE thread_id = %s
            """, (thread_id,))
            result = cursor.fetchone()
            
            if result:
                cursor.close()
                connection.close()
                return result
            else:
                # Thread doesn't exist, create new one
                cursor.execute("""
                    INSERT INTO conversations (thread_id, session_id, title) 
                    VALUES (%s, %s, %s)
                """, (thread_id, session_id, f"Conversation {datetime.now().strftime('%Y-%m-%d %H:%M')}"))
                new_thread_id = cursor.lastrowid
                cursor.close()
                connection.close()
                
                return {
                    'id': new_thread_id,
                    'thread_id': thread_id,
                    'session_id': session_id,
                    'title': f"Conversation {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                    'created_at': datetime.now()
                }
        else:
            # Create new thread with generated ID
            new_thread_id = generate_thread_id()
            cursor.execute("""
                INSERT INTO conversations (thread_id, session_id, title) 
                VALUES (%s, %s, %s)
            """, (new_thread_id, session_id, f"Conversation {datetime.now().strftime('%Y-%m-%d %H:%M')}"))
            conversation_id = cursor.lastrowid
            cursor.close()
            connection.close()
            
            return {
                'id': conversation_id,
                'thread_id': new_thread_id,
                'session_id': session_id,
                'title': f"Conversation {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                'created_at': datetime.now()
            }
        
    except Error as e:
        print(f"Error in get_or_create_thread: {e}")
        return None

def save_message_to_db(thread_id, role, content):
    """Save message to MySQL database with thread_id"""
    connection = get_mysql_connection()
    if not connection:
        return None
    
    try:
        cursor = connection.cursor()
        
        # Get conversation ID for this thread
        cursor.execute("SELECT id FROM conversations WHERE thread_id = %s", (thread_id,))
        result = cursor.fetchone()
        
        if not result:
            print(f"Thread {thread_id} not found")
            return None
        
        conversation_id = result[0]
        
        # Save message with thread_id
        cursor.execute(
            "INSERT INTO messages (conversation_id, thread_id, role, content) VALUES (%s, %s, %s, %s)",
            (conversation_id, thread_id, role, content)
        )
        
        connection.commit()
        cursor.close()
        connection.close()
        return conversation_id
        
    except Error as e:
        print(f"Error saving message to database: {e}")
        return None

def get_conversation_history(thread_id):
    """Get conversation history from database for a specific thread"""
    connection = get_mysql_connection()
    if not connection:
        return []
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT m.role, m.content, m.created_at 
            FROM messages m 
            WHERE m.thread_id = %s 
            ORDER BY m.created_at ASC
        """, (thread_id,))
        
        messages = cursor.fetchall()
        cursor.close()
        connection.close()
        return messages
        
    except Error as e:
        print(f"Error getting conversation history: {e}")
        return []

def get_user_threads(session_id):
    """Get all threads for a user session"""
    connection = get_mysql_connection()
    if not connection:
        return []
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT c.thread_id, c.title, c.created_at, c.updated_at,
                   COUNT(m.id) as message_count
            FROM conversations c
            LEFT JOIN messages m ON c.thread_id = m.thread_id
            WHERE c.session_id = %s
            GROUP BY c.thread_id, c.title, c.created_at, c.updated_at
            ORDER BY c.updated_at DESC
        """, (session_id,))
        
        threads = cursor.fetchall()
        cursor.close()
        connection.close()
        return threads
        
    except Error as e:
        print(f"Error getting user threads: {e}")
        return []

@app.route('/', methods=['GET'])
def root():
    """Simple root endpoint for basic connectivity testing"""
    return jsonify({
        'message': "Burdy's Auto Detail Chatbot API is running",
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'environment': os.getenv('RAILWAY_ENVIRONMENT', 'development'),
        'port': os.getenv('PORT', '5007')
    }), 200

@app.route('/ping', methods=['GET'])
def ping():
    """Simple ping endpoint for Railway health checks"""
    return jsonify({
        'pong': True,
        'timestamp': datetime.now().isoformat()
    }), 200

@app.route('/process_message', methods=['POST'])
def process_message():
    """Process chat message with OpenAI and save to MySQL with thread support"""
    try:
        data = request.json
        message = data.get('message')
        session_id = data.get('session_id', 'default_session')
        thread_id = data.get('thread_id')  # Can be None for new conversations
        
        if not message:
            return jsonify({'error': 'Message is required'}), 400
        
        # Get or create thread
        thread_info = get_or_create_thread(session_id, thread_id)
        if not thread_info:
            return jsonify({'error': 'Failed to create or retrieve thread'}), 500
        
        thread_id = thread_info['thread_id']
        
        # Save user message to database
        try:
            save_message_to_db(thread_id, 'user', message)
            # Get conversation history for context
            history = get_conversation_history(thread_id)
        except Exception as e:
            print(f"Database operation failed: {e}")
            history = []
        
        # Use OpenAI Assistants API
        try:
            if not assistant_id:
                return jsonify({'error': 'OpenAI Assistant ID not configured'}), 500
            
            # Create or get thread for this conversation
            if not thread_id:
                # Create new thread
                thread = client.beta.threads.create()
                thread_id = thread.id
            else:
                # Use existing thread
                try:
                    thread = client.beta.threads.retrieve(thread_id)
                except Exception:
                    # Thread doesn't exist, create new one
                    thread = client.beta.threads.create()
                    thread_id = thread.id
            
            # Add user message to thread
            client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=message
            )
            
            # Run the assistant
            run = client.beta.threads.runs.create(
                thread_id=thread_id,
                assistant_id=assistant_id
            )
            
            # Wait for the run to complete
            while True:
                run_status = client.beta.threads.runs.retrieve(
                    thread_id=thread_id,
                    run_id=run.id
                )
                
                if run_status.status == 'completed':
                    break
                elif run_status.status == 'failed':
                    raise Exception("Assistant run failed")
                elif run_status.status == 'requires_action':
                    raise Exception("Assistant requires action")
                
                import time
                time.sleep(1)  # Wait 1 second before checking again
            
            # Get the assistant's response
            messages = client.beta.threads.messages.list(thread_id=thread_id)
            assistant_response = messages.data[0].content[0].text.value
            
        except Exception as e:
            print(f"OpenAI Assistants API error: {e}")
            return jsonify({'error': 'Failed to get response from OpenAI Assistant'}), 500
        
        # Save assistant response to database
        try:
            save_message_to_db(thread_id, 'assistant', assistant_response)
        except Exception as e:
            print(f"Failed to save assistant response to database: {e}")
        
        return jsonify({
            'response': assistant_response,
            'session_id': session_id,
            'thread_id': thread_id,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        print(f"Error processing message: {e}")
        return jsonify({'error': 'Failed to process message'}), 500

@app.route('/health', methods=['GET'])
def health():
    """Comprehensive health check endpoint for Railway deployment"""
    try:
        # Check database connectivity
        db_status = "healthy"
        try:
            connection = get_mysql_connection()
            if connection:
                connection.close()
            else:
                db_status = "unhealthy"
        except Exception as e:
            print(f"Database health check failed: {e}")
            db_status = "unhealthy"
        
        # Check OpenAI connectivity (minimal check)
        openai_status = "healthy"
        try:
            # Check if API key and Assistant ID are set
            if not os.getenv('OPENAI_API_KEY'):
                openai_status = "unhealthy - Missing API Key"
            elif not os.getenv('OPENAI_ASSISTANT_ID'):
                openai_status = "unhealthy - Missing Assistant ID"
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

@app.route('/test-db', methods=['GET'])
def test_database():
    """Test database connection endpoint for debugging Railway deployment"""
    try:
        # Import the test function
        from railway_db_test import test_mysql_connection, get_railway_info
        
        # Capture output
        import io
        import sys
        
        # Redirect stdout to capture output
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        
        try:
            get_railway_info()
            success = test_mysql_connection()
            output = sys.stdout.getvalue()
        finally:
            sys.stdout = old_stdout
        
        return jsonify({
            'success': success,
            'output': output,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/conversation/<thread_id>', methods=['GET'])
def get_conversation(thread_id):
    """Get conversation history for a specific thread"""
    try:
        messages = get_conversation_history(thread_id)
        return jsonify({
            'thread_id': thread_id,
            'messages': messages
        }), 200
    except Exception as e:
        return jsonify({'error': 'Failed to get conversation'}), 500

@app.route('/threads/<session_id>', methods=['GET'])
def get_threads(session_id):
    """Get all threads for a user session"""
    try:
        threads = get_user_threads(session_id)
        return jsonify({
            'session_id': session_id,
            'threads': threads
        }), 200
    except Exception as e:
        return jsonify({'error': 'Failed to get threads'}), 500

@app.route('/thread/<thread_id>', methods=['DELETE'])
def delete_thread(thread_id):
    """Delete a specific thread and all its messages"""
    connection = get_mysql_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = connection.cursor()
        
        # Delete the conversation (messages will be deleted via CASCADE)
        cursor.execute("DELETE FROM conversations WHERE thread_id = %s", (thread_id,))
        
        if cursor.rowcount == 0:
            return jsonify({'error': 'Thread not found'}), 404
        
        connection.commit()
        cursor.close()
        connection.close()
        
        return jsonify({
            'message': 'Thread deleted successfully',
            'thread_id': thread_id
        }), 200
        
    except Error as e:
        print(f"Error deleting thread: {e}")
        return jsonify({'error': 'Failed to delete thread'}), 500

# This module is designed to be imported by start.py
# The Flask app will be started by the startup script 