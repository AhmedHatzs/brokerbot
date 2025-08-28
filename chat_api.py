#!/usr/bin/env python3
"""
Burdy's Auto Detail Chatbot API
Backend API with MySQL and OpenAI integration

Features:
- Text message processing with OpenAI Assistants API
- File upload support with intelligent text extraction
  - Text files (txt, md): Direct text extraction
  - PDF files: PyPDF2 text extraction + OCR fallback
  - Word documents (doc, docx): OCR processing
  - Image files (png, jpg, jpeg, gif, bmp, tiff): Tesseract OCR
  - All extracted text is sent to OpenAI for analysis
- File persistence and retrieval across conversations
- Thread-based conversation management
- MySQL database persistence for messages and files
- Session management
- Multi-format text extraction with OCR fallback

API Endpoints:
- POST /process_message - Process text messages or file uploads (supports both JSON and multipart form data)
- GET /files/<file_id> - Get file information
- DELETE /files/<file_id> - Delete files from OpenAI
- GET /conversation/<thread_id> - Get conversation history with files
- GET /thread/<thread_id>/files - Get all files for a thread
- GET /threads/<session_id> - Get user threads
- DELETE /thread/<thread_id> - Delete a thread
- GET /health - Health check
- GET /ping - Simple ping endpoint

Payload for /process_message:

JSON Format:
{
    "message": "Optional text message",
    "session_id": "User session ID",
    "thread_id": "Optional thread ID for continuing conversation"
}

Multipart Form Data:
- message: "Optional text message"
- session_id: "User session ID"
- thread_id: "Optional thread ID for continuing conversation"
- fileUpload: "File to upload and process"

Note: Either message or fileUpload must be provided, but both are optional.
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
import io
import pytesseract
from PIL import Image
import tempfile
import PyPDF2
from pdf2image import convert_from_bytes

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
assistant_id = os.getenv('OPENAI_ASSISTANT_ID')

# Helper function to create client with beta headers
def get_openai_client():
    client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    # Set beta header directly on the client
    if hasattr(client, '_client') and hasattr(client._client, 'headers'):
        client._client.headers["OpenAI-Beta"] = "assistants=v2"
    return client

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
        
        # Create messages table with file support
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INT AUTO_INCREMENT PRIMARY KEY,
                conversation_id INT,
                thread_id VARCHAR(255) NOT NULL,
                role ENUM('user', 'assistant') NOT NULL,
                content TEXT NOT NULL,
                file_id VARCHAR(255) DEFAULT NULL,
                filename VARCHAR(255) DEFAULT NULL,
                file_size INT DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
                INDEX idx_thread_id (thread_id),
                INDEX idx_conversation_id (conversation_id),
                INDEX idx_file_id (file_id)
            )
        """)
        
        # Create files table for file metadata
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS files (
                id INT AUTO_INCREMENT PRIMARY KEY,
                file_id VARCHAR(255) UNIQUE NOT NULL,
                filename VARCHAR(255) NOT NULL,
                file_size INT NOT NULL,
                file_type VARCHAR(50) NOT NULL,
                thread_id VARCHAR(255) NOT NULL,
                session_id VARCHAR(255) NOT NULL,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_file_id (file_id),
                INDEX idx_thread_id (thread_id),
                INDEX idx_session_id (session_id)
            )
        """)
        
        # Add missing columns to existing messages table if they don't exist
        try:
            cursor.execute("ALTER TABLE messages ADD COLUMN file_id VARCHAR(255) DEFAULT NULL")
            print("✅ Added file_id column to messages table")
        except Error as e:
            if "Duplicate column name" not in str(e):
                print(f"⚠️  Error adding file_id column: {e}")
        
        try:
            cursor.execute("ALTER TABLE messages ADD COLUMN filename VARCHAR(255) DEFAULT NULL")
            print("✅ Added filename column to messages table")
        except Error as e:
            if "Duplicate column name" not in str(e):
                print(f"⚠️  Error adding filename column: {e}")
        
        try:
            cursor.execute("ALTER TABLE messages ADD COLUMN file_size INT DEFAULT NULL")
            print("✅ Added file_size column to messages table")
        except Error as e:
            if "Duplicate column name" not in str(e):
                print(f"⚠️  Error adding file_size column: {e}")
        
        # Add index for file_id if it doesn't exist
        try:
            cursor.execute("CREATE INDEX idx_file_id ON messages (file_id)")
            print("✅ Added file_id index to messages table")
        except Error as e:
            if "Duplicate key name" not in str(e):
                print(f"⚠️  Error adding file_id index: {e}")
        
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

def clean_response_text(response_text):
    """
    Clean up OpenAI response text to remove formatting artifacts and citations
    
    Args:
        response_text: Raw response text from OpenAI
        
    Returns:
        str: Cleaned response text
    """
    if not response_text:
        return response_text
    
    import re
    
    # First, replace escaped characters
    response_text = response_text.replace('\\"', '"')
    response_text = response_text.replace('\\n', ' ')
    response_text = response_text.replace('\\t', ' ')
    
    # Remove specific citation patterns (more precise)
    response_text = re.sub(r'【\d+:\d+†source】', '', response_text)  # 【4:0†source】
    response_text = re.sub(r'\[\d+:\d+\]', '', response_text)        # [4:0]
    response_text = re.sub(r'\(\d+:\d+\)', '', response_text)        # (4:0)
    response_text = re.sub(r'†', '', response_text)                  # † symbol
    
    # Remove any remaining 【】 brackets that might contain other content
    response_text = re.sub(r'【[^】]*】', '', response_text)
    
    # Normalize whitespace (but preserve sentence structure)
    response_text = re.sub(r'\s+', ' ', response_text)
    
    # Clean up any double spaces around punctuation
    response_text = re.sub(r'\s+([.,!?])', r'\1', response_text)
    
    return response_text.strip()

def extract_text_from_file(file_obj, filename):
    """
    Extract text from any file using appropriate method based on file type
    
    Args:
        file_obj: File object containing any file type
        filename: Name of the file to determine type
        
    Returns:
        str: Extracted text from the file, or None if extraction fails
    """
    try:
        # Reset file pointer to beginning
        file_obj.seek(0)
        
        # Get file extension
        file_extension = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        
        # Read file content
        file_content = file_obj.read()
        file_obj.seek(0)  # Reset pointer again
        
        extracted_text = ""
        
        if file_extension in {'pdf'}:
            # Handle PDF files
            print(f"📄 Processing PDF file: {filename}")
            try:
                # First try to extract text directly from PDF
                pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
                for page in pdf_reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        extracted_text += page_text + "\n"
                
                # If no text extracted, try OCR on PDF pages
                if not extracted_text.strip():
                    print("📄 No text found in PDF, trying OCR on pages...")
                    images = convert_from_bytes(file_content)
                    for i, image in enumerate(images):
                        page_text = pytesseract.image_to_string(image)
                        if page_text:
                            extracted_text += f"Page {i+1}: {page_text}\n"
                
            except Exception as e:
                print(f"⚠️  PDF text extraction failed, trying OCR: {e}")
                # Fallback to OCR
                try:
                    images = convert_from_bytes(file_content)
                    for i, image in enumerate(images):
                        page_text = pytesseract.image_to_string(image)
                        if page_text:
                            extracted_text += f"Page {i+1}: {page_text}\n"
                except Exception as ocr_error:
                    print(f"❌ PDF OCR failed: {ocr_error}")
                    return None
                    
        elif file_extension in {'txt', 'md'}:
            # Handle text files directly
            print(f"📄 Processing text file: {filename}")
            try:
                # Try to decode as text
                extracted_text = file_content.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    extracted_text = file_content.decode('latin-1')
                except:
                    print("❌ Could not decode text file")
                    return None
                    
        elif file_extension in {'doc', 'docx'}:
            # Handle Word documents - convert to text first
            print(f"📄 Processing Word document: {filename}")
            # For now, we'll need to convert these to PDF or images first
            # This is a simplified approach - in production you might want to use python-docx
            try:
                # Try OCR on the document as if it were an image
                image = Image.open(io.BytesIO(file_content))
                extracted_text = pytesseract.image_to_string(image)
            except Exception as e:
                print(f"❌ Word document processing failed: {e}")
                return None
                
        else:
            # Handle image files (png, jpg, jpeg, gif, bmp, tiff)
            print(f"🖼️  Processing image file: {filename}")
            try:
                image = Image.open(io.BytesIO(file_content))
                extracted_text = pytesseract.image_to_string(image)
            except Exception as e:
                print(f"❌ Image processing failed: {e}")
                return None
        
        # Clean up the extracted text
        if extracted_text and extracted_text.strip():
            # Remove extra whitespace and normalize
            cleaned_text = ' '.join(extracted_text.split())
            print(f"✅ Text extraction successful: {len(cleaned_text)} characters extracted")
            return cleaned_text
        else:
            print("⚠️  Text extraction returned empty text")
            return None
            
    except Exception as e:
        print(f"❌ Text extraction failed: {e}")
        return None

def generate_thread_id():
    """Generate a unique thread ID for conversations"""
    return f"thread_{str(uuid.uuid4())}"

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

def save_message_to_db(thread_id, role, content, file_id=None, filename=None, file_size=None):
    """Save message to MySQL database with thread_id and optional file information"""
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
        
        # Try to save with file information first
        try:
            cursor.execute(
                "INSERT INTO messages (conversation_id, thread_id, role, content, file_id, filename, file_size) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (conversation_id, thread_id, role, content, file_id, filename, file_size)
            )
        except Error as e:
            if "Unknown column" in str(e):
                # Fallback to old schema if new columns don't exist
                print("⚠️  Using fallback schema for message save")
                cursor.execute(
                    "INSERT INTO messages (conversation_id, thread_id, role, content) VALUES (%s, %s, %s, %s)",
                    (conversation_id, thread_id, role, content)
                )
            else:
                raise e
        
        connection.commit()
        cursor.close()
        connection.close()
        return conversation_id
        
    except Error as e:
        print(f"Error saving message to database: {e}")
        return None

def save_file_to_db(file_id, filename, file_size, file_type, thread_id, session_id):
    """Save file metadata to MySQL database"""
    connection = get_mysql_connection()
    if not connection:
        return None
    
    try:
        cursor = connection.cursor()
        
        # Try to save file metadata
        try:
            cursor.execute(
                "INSERT INTO files (file_id, filename, file_size, file_type, thread_id, session_id) VALUES (%s, %s, %s, %s, %s, %s)",
                (file_id, filename, file_size, file_type, thread_id, session_id)
            )
        except Error as e:
            if "doesn't exist" in str(e) or "Unknown table" in str(e):
                print("⚠️  Files table doesn't exist yet, skipping file metadata save")
                return True  # Don't fail the whole operation
            else:
                raise e
        
        connection.commit()
        cursor.close()
        connection.close()
        return True
        
    except Error as e:
        print(f"Error saving file to database: {e}")
        return None

def get_thread_files(thread_id):
    """Get all files associated with a thread"""
    connection = get_mysql_connection()
    if not connection:
        return []
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        # Check if files table exists
        try:
            cursor.execute("""
                SELECT file_id, filename, file_size, file_type, uploaded_at 
                FROM files 
                WHERE thread_id = %s 
                ORDER BY uploaded_at ASC
            """, (thread_id,))
        except Error as e:
            if "doesn't exist" in str(e) or "Unknown table" in str(e):
                print("⚠️  Files table doesn't exist yet, returning empty list")
                return []
            else:
                raise e
        
        files = cursor.fetchall()
        cursor.close()
        connection.close()
        return files
        
    except Error as e:
        print(f"Error getting thread files: {e}")
        return []

def get_conversation_history(thread_id):
    """Get conversation history from database for a specific thread"""
    connection = get_mysql_connection()
    if not connection:
        return []
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        # Try with new columns first
        try:
            cursor.execute("""
                SELECT m.role, m.content, m.file_id, m.filename, m.file_size, m.created_at 
                FROM messages m 
                WHERE m.thread_id = %s 
                ORDER BY m.created_at ASC
            """, (thread_id,))
        except Error as e:
            if "Unknown column" in str(e):
                # Fallback to old schema if new columns don't exist
                print("⚠️  Using fallback schema for conversation history")
                cursor.execute("""
                    SELECT m.role, m.content, m.created_at 
                    FROM messages m 
                    WHERE m.thread_id = %s 
                    ORDER BY m.created_at ASC
                """, (thread_id,))
            else:
                raise e
        
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

@app.route('/test-file-upload', methods=['POST'])
def test_file_upload():
    """Test endpoint for file upload functionality"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Validate file type and size
        supported_extensions = {'txt', 'pdf', 'doc', 'docx', 'md', 'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'}
        
        file_extension = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
        
        if file_extension not in supported_extensions:
            return jsonify({'error': f'File type not allowed. Allowed types: {", ".join(supported_extensions)}'}), 400
        
        # Check file size
        file.seek(0, 2)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > 20 * 1024 * 1024:
            return jsonify({'error': 'File size too large. Maximum size is 20MB'}), 400
        
        # Test file processing using OCR for all files
        try:
            # Test OCR extraction for all file types
            extracted_text = extract_text_from_file(file, file.filename)
            
            if extracted_text:
                print(f"✅ OCR test successful: {len(extracted_text)} characters extracted")
            else:
                return jsonify({
                    'success': False,
                    'error': 'OCR extraction failed during test',
                    'filename': file.filename,
                    'size': file_size,
                    'type': file_extension
                }), 500
            
            return jsonify({
                'success': True,
                'message': 'File upload test successful',
                'filename': file.filename,
                'size': file_size,
                'type': file_extension,
                'timestamp': datetime.now().isoformat()
            }), 200
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'OpenAI upload test failed: {str(e)}',
                'filename': file.filename,
                'size': file_size,
                'type': file_extension
            }), 500
        
    except Exception as e:
        return jsonify({'error': f'Test failed: {str(e)}'}), 500

@app.route('/process_message', methods=['POST'])
def process_message():
    """Process chat message with OpenAI and save to MySQL with thread support"""
    try:
        # Handle both JSON and multipart form data
        if request.content_type and 'multipart/form-data' in request.content_type:
            # Handle file upload in multipart form
            message = request.form.get('message')
            session_id = request.form.get('session_id', 'default_session')
            thread_id = request.form.get('thread_id')
            file_upload = request.files.get('fileUpload')  # File object
        else:
            # Handle JSON payload
            data = request.json
            message = data.get('message')
            session_id = data.get('session_id', 'default_session')
            thread_id = data.get('thread_id')
            file_upload = None
        
        # Validate that either message or fileUpload is provided
        if not message and not file_upload:
            return jsonify({'error': 'Either message or fileUpload is required'}), 400
        
        # Get or create thread
        thread_info = get_or_create_thread(session_id, thread_id)
        if not thread_info:
            return jsonify({'error': 'Failed to create or retrieve thread'}), 500
        
        thread_id = thread_info['thread_id']
        
        # Handle file upload if present
        file_id = None
        extracted_text = None
        if file_upload:
            try:
                # Define supported file types (all will use OCR)
                supported_extensions = {'txt', 'pdf', 'doc', 'docx', 'md', 'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'}
                
                file_extension = file_upload.filename.rsplit('.', 1)[1].lower() if '.' in file_upload.filename else ''
                
                if file_extension not in supported_extensions:
                    return jsonify({'error': f'File type not supported. Supported types: {", ".join(supported_extensions)}'}), 400
                
                # Check file size (max 20MB for OpenAI)
                file_upload.seek(0, 2)  # Seek to end
                file_size = file_upload.tell()
                file_upload.seek(0)  # Reset to beginning
                
                if file_size > 20 * 1024 * 1024:  # 20MB limit
                    return jsonify({'error': 'File size too large. Maximum size is 20MB'}), 400
                
                # Process all files using OCR
                print(f"📄 Processing file with OCR: {file_upload.filename}")
                
                # Extract text from file using OCR
                extracted_text = extract_text_from_file(file_upload, file_upload.filename)
                
                if extracted_text:
                    # Create a temporary text file with extracted content for OpenAI
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_file:
                        temp_file.write(extracted_text)
                        temp_file_path = temp_file.name
                    
                    try:
                        # Upload the extracted text as a text file to OpenAI
                        openai_client = get_openai_client()
                        
                        with open(temp_file_path, 'rb') as text_file:
                            file_obj = io.BytesIO(text_file.read())
                            file_obj.name = f"{file_upload.filename}_extracted.txt"
                            
                            uploaded_file = openai_client.files.create(
                                file=file_obj,
                                purpose="assistants"
                            )
                            file_id = uploaded_file.id
                            print(f"✅ File text extracted and uploaded: {file_upload.filename} -> {file_id}")
                            
                    finally:
                        # Clean up temporary file
                        if os.path.exists(temp_file_path):
                            os.unlink(temp_file_path)
                else:
                    return jsonify({'error': 'Failed to extract text from file. Please ensure the file contains readable text.'}), 400
                
                print(f"📊 File size: {file_size} bytes, Type: {file_extension}")
                
                # Save file metadata to database
                save_file_to_db(file_id, file_upload.filename, file_size, file_extension, thread_id, session_id)
                
            except Exception as e:
                print(f"File upload error: {e}")
                print(f"File details - Name: {file_upload.filename}, Size: {file_size}, Type: {file_extension}")
                return jsonify({'error': f'Failed to upload file to OpenAI: {str(e)}'}), 500
        
        # Prepare content for database and OpenAI
        if file_upload and extracted_text:
            # For all files, include the extracted text in the user message with clear instructions
            user_content = f"""File uploaded: {file_upload.filename}

Extracted text from file:
{extracted_text}

{message if message else 'Please analyze this text and provide a clear, professional response without any formatting artifacts or citations.'}

Please provide a clean, readable response without any source citations or formatting artifacts."""
        else:
            user_content = message if message else f"File uploaded: {file_upload.filename if file_upload else 'Unknown file'}"
        
        # Save user message to database with file information
        try:
            save_message_to_db(thread_id, 'user', user_content, file_id, file_upload.filename if file_upload else None, file_size if file_upload else None)
            # Get conversation history for context
            history = get_conversation_history(thread_id)
        except Exception as e:
            print(f"Database operation failed: {e}")
            history = []
        
        # Use OpenAI Assistants API
        try:
            if not assistant_id:
                return jsonify({'error': 'OpenAI Assistant ID not configured'}), 500
            
            # Get client with beta headers
            openai_client = get_openai_client()
            print(f"🔧 OpenAI client created with headers: {openai_client._client.headers.get('OpenAI-Beta', 'NOT SET')}")
            print(f"🔧 All headers: {dict(openai_client._client.headers)}")
            
            # Create or get thread for this conversation
            if not thread_id:
                # Create new thread
                thread = openai_client.beta.threads.create()
                thread_id = thread.id
                print(f"🆕 Created new OpenAI thread: {thread_id}")
            else:
                # Use existing thread - check if it's a valid OpenAI thread ID
                if not thread_id.startswith('thread_'):
                    print(f"⚠️  Invalid thread ID format: {thread_id}, creating new OpenAI thread")
                    thread = openai_client.beta.threads.create()
                    thread_id = thread.id
                    print(f"🆕 Created new OpenAI thread: {thread_id}")
                else:
                    try:
                        thread = openai_client.beta.threads.retrieve(thread_id)
                        print(f"📋 Retrieved existing OpenAI thread: {thread_id}")
                    except Exception as e:
                        print(f"⚠️  Thread {thread_id} not found in OpenAI, creating new one: {e}")
                        # Thread doesn't exist, create new one
                        thread = openai_client.beta.threads.create()
                        thread_id = thread.id
                        print(f"🆕 Created new OpenAI thread: {thread_id}")
            
            # Get all files from thread history to attach to the message
            thread_files = get_thread_files(thread_id)
            file_ids_to_attach = []
            
            # Add current file if present
            if file_id:
                file_ids_to_attach.append(file_id)
                print(f"📎 Adding current file: {file_id}")
            
            # Add files from thread history (so AI can reference previous files)
            for file_info in thread_files:
                if file_info['file_id'] not in file_ids_to_attach:
                    file_ids_to_attach.append(file_info['file_id'])
                    print(f"📎 Adding historical file: {file_info['file_id']}")
            
            # Add user message to thread with all relevant files
            if file_ids_to_attach:
                # Handle message with file attachments
                print(f"🔧 Creating message with {len(file_ids_to_attach)} files: {file_ids_to_attach}")
                try:
                    # Use the correct API format for file attachments
                    openai_client.beta.threads.messages.create(
                        thread_id=thread_id,
                        role="user",
                        content=message or "Please analyze this file",
                        attachments=[{"file_id": file_id, "tools": [{"type": "file_search"}]} for file_id in file_ids_to_attach]
                    )
                    print(f"✅ Message created successfully with files")
                except Exception as msg_error:
                    print(f"❌ Error creating message with files: {msg_error}")
                    # Fallback to message without files
                    openai_client.beta.threads.messages.create(
                        thread_id=thread_id,
                        role="user",
                        content=message or "Please analyze this file"
                    )
                    print(f"✅ Message created without files (fallback)")
            else:
                # Handle text message only
                openai_client.beta.threads.messages.create(
                    thread_id=thread_id,
                    role="user",
                    content=message
                )
            
            # Run the assistant
            run = openai_client.beta.threads.runs.create(
                thread_id=thread_id,
                assistant_id=assistant_id
            )
            
            # Wait for the run to complete
            while True:
                run_status = openai_client.beta.threads.runs.retrieve(
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
            messages = openai_client.beta.threads.messages.list(thread_id=thread_id)
            assistant_response = messages.data[0].content[0].text.value
            
            # Clean up the response to remove formatting artifacts and citations
            assistant_response = clean_response_text(assistant_response)
            
        except Exception as e:
            print(f"OpenAI Assistants API error: {e}")
            print(f"Error type: {type(e)}")
            print(f"Error details: {str(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return jsonify({'error': f'Failed to get response from OpenAI Assistant: {str(e)}'}), 500
        
        # Save assistant response to database
        try:
            save_message_to_db(thread_id, 'assistant', assistant_response, None, None, None)
        except Exception as e:
            print(f"Failed to save assistant response to database: {e}")
        
        response_data = {
            'response': assistant_response,
            'session_id': session_id,
            'thread_id': thread_id,
            'timestamp': datetime.now().isoformat()
        }
        
        # Add file information if a file was uploaded
        if file_id:
            response_data['file_uploaded'] = True
            response_data['file_id'] = file_id
            response_data['filename'] = file_upload.filename if file_upload else 'Unknown'
        
        return jsonify(response_data), 200
        
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
        files = get_thread_files(thread_id)
        return jsonify({
            'thread_id': thread_id,
            'messages': messages,
            'files': files
        }), 200
    except Exception as e:
        return jsonify({'error': 'Failed to get conversation'}), 500

@app.route('/thread/<thread_id>/files', methods=['GET'])
def get_thread_files_endpoint(thread_id):
    """Get all files associated with a specific thread"""
    try:
        files = get_thread_files(thread_id)
        return jsonify({
            'thread_id': thread_id,
            'files': files
        }), 200
    except Exception as e:
        return jsonify({'error': 'Failed to get thread files'}), 500

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



@app.route('/files/<file_id>', methods=['DELETE'])
def delete_file(file_id):
    """Delete a file from OpenAI"""
    try:
        openai_client = get_openai_client()
        openai_client.files.delete(file_id)
        
        return jsonify({
            'message': 'File deleted successfully',
            'file_id': file_id,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        print(f"File deletion error: {e}")
        return jsonify({'error': 'Failed to delete file'}), 500

@app.route('/files/<file_id>', methods=['GET'])
def get_file_info(file_id):
    """Get information about a specific file"""
    try:
        openai_client = get_openai_client()
        file_info = openai_client.files.retrieve(file_id)
        
        return jsonify({
            'file_id': file_info.id,
            'filename': file_info.filename,
            'size': file_info.bytes,
            'purpose': file_info.purpose,
            'created_at': file_info.created_at,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        print(f"File info retrieval error: {e}")
        return jsonify({'error': 'Failed to get file information'}), 500

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