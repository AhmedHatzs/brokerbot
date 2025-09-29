#!/usr/bin/env python3
"""
Brokerbot Chatbot API
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
- POST /process_message - Process text messages, file uploads, or file URLs (supports both JSON and multipart form data)
- POST /test-file-upload - Test file upload functionality
- POST /test-url-download - Test URL file download functionality
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
    "thread_id": "Optional thread ID for continuing conversation",
    "fileUrl": "Optional URL to a file to download and process"
}

Multipart Form Data:
- message: "Optional text message"
- session_id: "User session ID"
- thread_id: "Optional thread ID for continuing conversation"
- fileUpload: "File to upload and process"
- fileUrl: "URL to a file to download and process"

Note: Either message, fileUpload, or fileUrl must be provided, but all are optional.
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
import requests
from urllib.parse import urlparse
import threading

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
validator_assistant_id = os.getenv('VALIDATOR_ASSISTANT')

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
            'connect_timeout': 30,  # Connection timeout
            'autocommit': True,
            'charset': 'utf8mb4',
            'collation': 'utf8mb4_unicode_ci',
            'sql_mode': 'TRADITIONAL',
            'init_command': "SET SESSION wait_timeout=28800, interactive_timeout=28800"  # 8 hours timeout
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
            'database': 'brokerbot',
            'user': 'root',
            'password': '',
            'ssl_disabled': True,
            'connect_timeout': 10,
            'autocommit': True
        }

MYSQL_CONFIG = get_mysql_config()

# Connection pool for better performance
_connection_pool = None
_pool_lock = threading.Lock()

def get_mysql_connection():
    """Get MySQL connection - always create fresh connection for reliability"""
    print(f"🔌 [GET_MYSQL_CONNECTION] Creating fresh database connection")
    print(f"🔌 [GET_MYSQL_CONNECTION] Config host: {MYSQL_CONFIG.get('host')}")
    print(f"🔌 [GET_MYSQL_CONNECTION] Config database: {MYSQL_CONFIG.get('database')}")
    print(f"🔌 [GET_MYSQL_CONNECTION] Config port: {MYSQL_CONFIG.get('port')}")
    
    try:
        # Always create fresh connection to avoid timeout issues
        connection = mysql.connector.connect(**MYSQL_CONFIG)
        print("✅ [GET_MYSQL_CONNECTION] Database connection successful")
        return connection
    except Error as e:
        print(f"❌ [GET_MYSQL_CONNECTION] MySQL Error connecting to database: {e}")
        # In production, log more details but don't expose sensitive info
        if os.getenv('RAILWAY_ENVIRONMENT') == 'production':
            print(f"❌ [GET_MYSQL_CONNECTION] Database connection failed - Host: {MYSQL_CONFIG.get('host')}, Database: {MYSQL_CONFIG.get('database')}")
        return None
    except Exception as e:
        print(f"❌ [GET_MYSQL_CONNECTION] Unexpected error connecting to MySQL: {e}")
        import traceback
        print(f"❌ [GET_MYSQL_CONNECTION] Connection error traceback: {traceback.format_exc()}")
        return None

def close_mysql_connection(connection=None):
    """Close MySQL connection safely"""
    if connection:
        try:
            connection.close()
            print("🔌 [CLOSE_MYSQL_CONNECTION] Connection closed")
        except Exception as e:
            print(f"⚠️ [CLOSE_MYSQL_CONNECTION] Error closing connection: {e}")
    
    # Also close pool if it exists
    global _connection_pool
    if _connection_pool:
        try:
            _connection_pool.close()
            print("🔌 [CLOSE_MYSQL_CONNECTION] Pool connection closed")
        except:
            pass
        finally:
            _connection_pool = None

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
        close_mysql_connection(connection)
        return True
        
    except Error as e:
        print(f"Error initializing database: {e}")
        if connection:
            close_mysql_connection(connection)
        return False

# Initialize database when app is created (for gunicorn compatibility)
print("🔧 Initializing database...")
import threading
import time

def init_db_background():
    """Initialize database in background thread with retry logic"""
    max_retries = 5  # Increased retries
    retry_delay = 10  # Increased delay between retries
    
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
            # Check if it's a connection timeout error
            if "Lost connection" in str(e) or "timeout" in str(e).lower():
                print("🔌 Connection timeout detected, will retry with fresh connection")
        
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
    print(f"🧹 [CLEAN_RESPONSE_TEXT] Starting response cleaning")
    print(f"🧹 [CLEAN_RESPONSE_TEXT] Original response length: {len(response_text) if response_text else 0}")
    
    if not response_text:
        print("🧹 [CLEAN_RESPONSE_TEXT] No response text to clean")
        return response_text
    
    import re
    
    # First, replace escaped characters
    print("🧹 [CLEAN_RESPONSE_TEXT] Replacing escaped characters")
    response_text = response_text.replace('\\"', '"')
    response_text = response_text.replace('\\n', ' ')
    response_text = response_text.replace('\\t', ' ')
    
    # Remove markdown code blocks (```json ... ```)
    print("🧹 [CLEAN_RESPONSE_TEXT] Removing markdown code blocks")
    response_text = re.sub(r'```json\s*', '', response_text)
    response_text = re.sub(r'```\s*$', '', response_text)
    
    # Remove specific citation patterns (more precise)
    print("🧹 [CLEAN_RESPONSE_TEXT] Removing citation patterns")
    response_text = re.sub(r'【\d+:\d+†source】', '', response_text)  # 【4:0†source】
    response_text = re.sub(r'\[\d+:\d+\]', '', response_text)        # [4:0]
    response_text = re.sub(r'\(\d+:\d+\)', '', response_text)        # (4:0)
    response_text = re.sub(r'†', '', response_text)                  # † symbol
    
    # Remove any remaining 【】 brackets that might contain other content
    response_text = re.sub(r'【[^】]*】', '', response_text)
    
    # Normalize whitespace (but preserve sentence structure)
    print("🧹 [CLEAN_RESPONSE_TEXT] Normalizing whitespace")
    response_text = re.sub(r'\s+', ' ', response_text)
    
    # Clean up any double spaces around punctuation
    response_text = re.sub(r'\s+([.,!?])', r'\1', response_text)
    
    cleaned_text = response_text.strip()
    print(f"🧹 [CLEAN_RESPONSE_TEXT] Cleaning completed - final length: {len(cleaned_text)}")
    
    return cleaned_text

def extract_text_from_file(file_obj, filename):
    """
    Extract text from any file using appropriate method based on file type
    
    Args:
        file_obj: File object containing any file type
        filename: Name of the file to determine type
        
    Returns:
        str: Extracted text from the file, or None if extraction fails
    """
    print(f"📄 [EXTRACT_TEXT_FROM_FILE] Starting text extraction for: {filename}")
    
    try:
        # Reset file pointer to beginning
        file_obj.seek(0)
        
        # Get file extension
        file_extension = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        print(f"📄 [EXTRACT_TEXT_FROM_FILE] File extension: {file_extension}")
        
        # Read file content
        file_content = file_obj.read()
        file_obj.seek(0)  # Reset pointer again
        print(f"📄 [EXTRACT_TEXT_FROM_FILE] File content size: {len(file_content)} bytes")
        
        extracted_text = ""
        
        if file_extension in {'pdf'}:
            # Handle PDF files
            print(f"📄 [EXTRACT_TEXT_FROM_FILE] Processing PDF file: {filename}")
            try:
                # First try to extract text directly from PDF
                print("📄 [EXTRACT_TEXT_FROM_FILE] Attempting direct PDF text extraction")
                pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
                print(f"📄 [EXTRACT_TEXT_FROM_FILE] PDF has {len(pdf_reader.pages)} pages")
                
                for page_num, page in enumerate(pdf_reader.pages):
                    page_text = page.extract_text()
                    if page_text:
                        extracted_text += page_text + "\n"
                        print(f"📄 [EXTRACT_TEXT_FROM_FILE] Page {page_num + 1}: {len(page_text)} characters extracted")
                    else:
                        print(f"📄 [EXTRACT_TEXT_FROM_FILE] Page {page_num + 1}: No text found")
                
                # If no text extracted, try OCR on PDF pages
                if not extracted_text.strip():
                    print("📄 [EXTRACT_TEXT_FROM_FILE] No text found in PDF, trying OCR on pages...")
                    images = convert_from_bytes(file_content)
                    print(f"📄 [EXTRACT_TEXT_FROM_FILE] Converted PDF to {len(images)} images for OCR")
                    
                    for i, image in enumerate(images):
                        print(f"📄 [EXTRACT_TEXT_FROM_FILE] Running OCR on page {i+1}")
                        page_text = pytesseract.image_to_string(image)
                        if page_text:
                            extracted_text += f"Page {i+1}: {page_text}\n"
                            print(f"📄 [EXTRACT_TEXT_FROM_FILE] Page {i+1} OCR: {len(page_text)} characters")
                        else:
                            print(f"📄 [EXTRACT_TEXT_FROM_FILE] Page {i+1} OCR: No text found")
                
            except Exception as e:
                print(f"⚠️ [EXTRACT_TEXT_FROM_FILE] PDF text extraction failed, trying OCR: {e}")
                # Fallback to OCR
                try:
                    print("📄 [EXTRACT_TEXT_FROM_FILE] Starting OCR fallback for PDF")
                    images = convert_from_bytes(file_content)
                    print(f"📄 [EXTRACT_TEXT_FROM_FILE] OCR fallback: Converted to {len(images)} images")
                    
                    for i, image in enumerate(images):
                        print(f"📄 [EXTRACT_TEXT_FROM_FILE] OCR fallback on page {i+1}")
                        page_text = pytesseract.image_to_string(image)
                        if page_text:
                            extracted_text += f"Page {i+1}: {page_text}\n"
                            print(f"📄 [EXTRACT_TEXT_FROM_FILE] OCR fallback page {i+1}: {len(page_text)} characters")
                        else:
                            print(f"📄 [EXTRACT_TEXT_FROM_FILE] OCR fallback page {i+1}: No text found")
                except Exception as ocr_error:
                    print(f"❌ [EXTRACT_TEXT_FROM_FILE] PDF OCR failed: {ocr_error}")
                    return None
                    
        elif file_extension in {'txt', 'md'}:
            # Handle text files directly
            print(f"📄 [EXTRACT_TEXT_FROM_FILE] Processing text file: {filename}")
            try:
                # Try to decode as text
                extracted_text = file_content.decode('utf-8')
                print(f"📄 [EXTRACT_TEXT_FROM_FILE] Text file decoded with UTF-8: {len(extracted_text)} characters")
            except UnicodeDecodeError:
                try:
                    extracted_text = file_content.decode('latin-1')
                    print(f"📄 [EXTRACT_TEXT_FROM_FILE] Text file decoded with Latin-1: {len(extracted_text)} characters")
                except:
                    print("❌ [EXTRACT_TEXT_FROM_FILE] Could not decode text file")
                    return None
                    
        elif file_extension in {'doc', 'docx'}:
            # Handle Word documents - convert to text first
            print(f"📄 [EXTRACT_TEXT_FROM_FILE] Processing Word document: {filename}")
            # For now, we'll need to convert these to PDF or images first
            # This is a simplified approach - in production you might want to use python-docx
            try:
                # Try OCR on the document as if it were an image
                print("📄 [EXTRACT_TEXT_FROM_FILE] Attempting OCR on Word document")
                image = Image.open(io.BytesIO(file_content))
                extracted_text = pytesseract.image_to_string(image)
                print(f"📄 [EXTRACT_TEXT_FROM_FILE] Word document OCR: {len(extracted_text)} characters")
            except Exception as e:
                print(f"❌ [EXTRACT_TEXT_FROM_FILE] Word document processing failed: {e}")
                return None
                
        else:
            # Handle image files (png, jpg, jpeg, gif, bmp, tiff)
            print(f"🖼️ [EXTRACT_TEXT_FROM_FILE] Processing image file: {filename}")
            try:
                image = Image.open(io.BytesIO(file_content))
                print(f"🖼️ [EXTRACT_TEXT_FROM_FILE] Image opened successfully: {image.size}")
                extracted_text = pytesseract.image_to_string(image)
                print(f"🖼️ [EXTRACT_TEXT_FROM_FILE] Image OCR: {len(extracted_text)} characters")
            except Exception as e:
                print(f"❌ [EXTRACT_TEXT_FROM_FILE] Image processing failed: {e}")
                return None
        
        # Clean up the extracted text
        if extracted_text and extracted_text.strip():
            # Remove extra whitespace and normalize
            cleaned_text = ' '.join(extracted_text.split())
            print(f"✅ [EXTRACT_TEXT_FROM_FILE] Text extraction successful: {len(cleaned_text)} characters extracted")
            return cleaned_text
        else:
            print("⚠️ [EXTRACT_TEXT_FROM_FILE] Text extraction returned empty text")
            return None
            
    except Exception as e:
        print(f"❌ [EXTRACT_TEXT_FROM_FILE] Text extraction failed: {e}")
        import traceback
        print(f"❌ [EXTRACT_TEXT_FROM_FILE] Text extraction error traceback: {traceback.format_exc()}")
        return None

def generate_thread_id():
    """Generate a unique thread ID for conversations"""
    return f"thread_{str(uuid.uuid4())}"

def get_or_create_thread(session_id, thread_id=None):
    """Get existing thread or create a new one"""
    print(f"🔄 [GET_OR_CREATE_THREAD] Starting with session_id: {session_id}, thread_id: {thread_id}")
    
    connection = get_mysql_connection()
    if not connection:
        print("❌ [GET_OR_CREATE_THREAD] Database connection failed")
        return None
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        if thread_id:
            print(f"🔍 [GET_OR_CREATE_THREAD] Looking for existing thread: {thread_id}")
            # Try to get existing thread
            cursor.execute("""
                SELECT id, thread_id, session_id, title, created_at 
                FROM conversations 
                WHERE thread_id = %s
            """, (thread_id,))
            result = cursor.fetchone()
            
            if result:
                print(f"✅ [GET_OR_CREATE_THREAD] Found existing thread: {thread_id}")
                cursor.close()
                connection.close()
                return result
            else:
                print(f"🆕 [GET_OR_CREATE_THREAD] Thread not found, creating new one with provided ID: {thread_id}")
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
            print("🆕 [GET_OR_CREATE_THREAD] No thread_id provided, creating new thread")
            # Create new thread with generated ID
            new_thread_id = generate_thread_id()
            print(f"🆕 [GET_OR_CREATE_THREAD] Generated new thread_id: {new_thread_id}")
            cursor.execute("""
                INSERT INTO conversations (thread_id, session_id, title) 
                VALUES (%s, %s, %s)
            """, (new_thread_id, session_id, f"Conversation {datetime.now().strftime('%Y-%m-%d %H:%M')}"))
            conversation_id = cursor.lastrowid
            cursor.close()
            connection.close()
            
            print(f"✅ [GET_OR_CREATE_THREAD] Created new thread with ID: {new_thread_id}")
            return {
                'id': conversation_id,
                'thread_id': new_thread_id,
                'session_id': session_id,
                'title': f"Conversation {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                'created_at': datetime.now()
            }
        
    except Error as e:
        print(f"❌ [GET_OR_CREATE_THREAD] Database error: {e}")
        import traceback
        print(f"❌ [GET_OR_CREATE_THREAD] Database error traceback: {traceback.format_exc()}")
        return None

def save_message_to_db(thread_id, role, content, file_id=None, filename=None, file_size=None):
    """Save message to MySQL database with thread_id and optional file information"""
    print(f"💾 [SAVE_MESSAGE_TO_DB] Starting save for thread_id: {thread_id}, role: {role}")
    print(f"💾 [SAVE_MESSAGE_TO_DB] Content length: {len(content) if content else 0}")
    print(f"💾 [SAVE_MESSAGE_TO_DB] File info - file_id: {file_id}, filename: {filename}, file_size: {file_size}")
    
    connection = get_mysql_connection()
    if not connection:
        print("❌ [SAVE_MESSAGE_TO_DB] Database connection failed")
        return None
    
    try:
        cursor = connection.cursor()
        
        # Get conversation ID for this thread
        print(f"🔍 [SAVE_MESSAGE_TO_DB] Looking up conversation ID for thread: {thread_id}")
        cursor.execute("SELECT id FROM conversations WHERE thread_id = %s", (thread_id,))
        result = cursor.fetchone()
        
        if not result:
            print(f"❌ [SAVE_MESSAGE_TO_DB] Thread {thread_id} not found in conversations table")
            return None
        
        conversation_id = result[0]
        print(f"✅ [SAVE_MESSAGE_TO_DB] Found conversation_id: {conversation_id}")
        
        # Try to save with file information first
        try:
            print("💾 [SAVE_MESSAGE_TO_DB] Attempting to save with file information")
            cursor.execute(
                "INSERT INTO messages (conversation_id, thread_id, role, content, file_id, filename, file_size) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (conversation_id, thread_id, role, content, file_id, filename, file_size)
            )
            print("✅ [SAVE_MESSAGE_TO_DB] Message saved successfully with file information")
        except Error as e:
            if "Unknown column" in str(e):
                # Fallback to old schema if new columns don't exist
                print("⚠️ [SAVE_MESSAGE_TO_DB] Using fallback schema for message save")
                cursor.execute(
                    "INSERT INTO messages (conversation_id, thread_id, role, content) VALUES (%s, %s, %s, %s)",
                    (conversation_id, thread_id, role, content)
                )
                print("✅ [SAVE_MESSAGE_TO_DB] Message saved successfully with fallback schema")
            else:
                print(f"❌ [SAVE_MESSAGE_TO_DB] Database error: {e}")
                raise e
        
        connection.commit()
        cursor.close()
        connection.close()
        print(f"✅ [SAVE_MESSAGE_TO_DB] Message save completed successfully")
        return conversation_id
        
    except Error as e:
        print(f"❌ [SAVE_MESSAGE_TO_DB] Error saving message to database: {e}")
        import traceback
        print(f"❌ [SAVE_MESSAGE_TO_DB] Database error traceback: {traceback.format_exc()}")
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

def get_or_create_openai_thread_mapping(database_thread_id, openai_thread_id):
    """
    Store mapping between database thread ID and OpenAI thread ID for conversation continuity
    
    Args:
        database_thread_id: The thread ID used in our database
        openai_thread_id: The thread ID used in OpenAI
        
    Returns:
        bool: True if mapping was stored successfully
    """
    connection = get_mysql_connection()
    if not connection:
        return False
    
    try:
        cursor = connection.cursor()
        
        # Check if conversations table has openai_thread_id column, if not add it
        try:
            cursor.execute("ALTER TABLE conversations ADD COLUMN openai_thread_id VARCHAR(255) DEFAULT NULL")
            print("✅ Added openai_thread_id column to conversations table")
        except Error as e:
            if "Duplicate column name" not in str(e):
                print(f"⚠️  Error adding openai_thread_id column: {e}")
        
        # Update the conversation record with the OpenAI thread ID
        cursor.execute("""
            UPDATE conversations 
            SET openai_thread_id = %s 
            WHERE thread_id = %s
        """, (openai_thread_id, database_thread_id))
        
        connection.commit()
        cursor.close()
        connection.close()
        print(f"✅ [THREAD_MAPPING] Mapped database thread {database_thread_id} to OpenAI thread {openai_thread_id}")
        return True
        
    except Error as e:
        print(f"❌ [THREAD_MAPPING] Error storing thread mapping: {e}")
        return False

def get_openai_thread_id(database_thread_id):
    """
    Get the OpenAI thread ID for a given database thread ID
    
    Args:
        database_thread_id: The thread ID used in our database
        
    Returns:
        str or None: The OpenAI thread ID if found, None otherwise
    """
    connection = get_mysql_connection()
    if not connection:
        return None
    
    try:
        cursor = connection.cursor()
        
        # Try to get the OpenAI thread ID
        try:
            cursor.execute("""
                SELECT openai_thread_id 
                FROM conversations 
                WHERE thread_id = %s AND openai_thread_id IS NOT NULL
            """, (database_thread_id,))
            result = cursor.fetchone()
            
            if result:
                openai_thread_id = result[0]
                print(f"✅ [THREAD_MAPPING] Found OpenAI thread ID: {openai_thread_id} for database thread: {database_thread_id}")
                return openai_thread_id
            else:
                print(f"⚠️ [THREAD_MAPPING] No OpenAI thread ID found for database thread: {database_thread_id}")
                return None
                
        except Error as e:
            if "Unknown column" in str(e):
                print("⚠️ [THREAD_MAPPING] openai_thread_id column doesn't exist yet")
                return None
            else:
                raise e
        
        cursor.close()
        connection.close()
        
    except Error as e:
        print(f"❌ [THREAD_MAPPING] Error getting OpenAI thread ID: {e}")
        return None

def sync_conversation_history_to_openai(openai_client, openai_thread_id, database_thread_id, max_messages=10):
    """
    Sync conversation history from database to OpenAI thread for context continuity
    This ensures OpenAI has the conversation context without sending it in every request
    
    Args:
        openai_client: OpenAI client instance
        openai_thread_id: The OpenAI thread ID
        database_thread_id: The database thread ID
        max_messages: Maximum number of recent messages to sync (default 10)
        
    Returns:
        bool: True if sync was successful, False otherwise
    """
    print(f"🔄 [SYNC_HISTORY] Starting conversation history sync for OpenAI thread: {openai_thread_id}")
    
    try:
        # Get recent conversation history from database
        history = get_conversation_history(database_thread_id)
        
        if not history:
            print("📋 [SYNC_HISTORY] No conversation history found in database")
            return True
        
        # Limit to recent messages to avoid token bloat
        recent_history = history[-max_messages:] if len(history) > max_messages else history
        print(f"📋 [SYNC_HISTORY] Syncing {len(recent_history)} recent messages to OpenAI thread")
        
        # Get existing messages in OpenAI thread
        existing_messages = openai_client.beta.threads.messages.list(thread_id=openai_thread_id)
        existing_count = len(existing_messages.data)
        print(f"📋 [SYNC_HISTORY] OpenAI thread currently has {existing_count} messages")
        
        # Only sync if we have more recent messages than what's in OpenAI
        if len(recent_history) <= existing_count:
            print("📋 [SYNC_HISTORY] OpenAI thread already has recent conversation history, skipping sync")
            return True
        
        # Add missing messages to OpenAI thread (only user messages for context)
        messages_added = 0
        for message in recent_history:
            if message['role'] == 'user' and messages_added < max_messages:
                try:
                    # Check if this message already exists in OpenAI thread
                    message_exists = any(
                        msg.content[0].text.value == message['content'] 
                        for msg in existing_messages.data 
                        if hasattr(msg.content[0], 'text')
                    )
                    
                    if not message_exists:
                        openai_client.beta.threads.messages.create(
                            thread_id=openai_thread_id,
                            role="user",
                            content=message['content']
                        )
                        messages_added += 1
                        print(f"📝 [SYNC_HISTORY] Added user message to OpenAI thread: {len(message['content'])} chars")
                        
                except Exception as e:
                    print(f"⚠️ [SYNC_HISTORY] Failed to add message to OpenAI thread: {e}")
                    continue
        
        print(f"✅ [SYNC_HISTORY] Successfully synced {messages_added} messages to OpenAI thread")
        return True
        
    except Exception as e:
        print(f"❌ [SYNC_HISTORY] Error syncing conversation history: {e}")
        return False

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

def detect_goodbye_message(response_text):
    """
    Detect if the assistant response contains goodbye indicators
    Only detects "goodbye" variations, not "bye" or other words
    
    Args:
        response_text: The assistant's response text
        
    Returns:
        bool: True if goodbye detected, False otherwise
    """
    if not response_text:
        return False
    
    import re
    
    # Convert to lowercase for case-insensitive matching
    response_lower = response_text.lower().strip()
    
    # Define regex patterns for "goodbye and take care" variations only
    # This will ONLY match the specific phrase "Goodbye and Take Care"
    # But NOT: goodbye alone, bye, see you later, take care alone, etc.
    goodbye_regex_patterns = [
        # Specific goodbye phrases from the prompt - MUST include "and take care"
        r'goodbye\s+and\s+take\s+care',           # "goodbye and take care"
        r'good\s*bye\s+and\s+take\s+care',       # "good bye and take care"
        r'good-bye\s+and\s+take\s+care',         # "good-bye and take care"
        r'goodby\s+and\s+take\s+care',           # "goodby and take care" (typo)
    ]
    
    # Check each regex pattern
    for pattern in goodbye_regex_patterns:
        if re.search(pattern, response_lower):
            match = re.search(pattern, response_lower)
            print(f"✅ [DETECT_GOODBYE] Regex pattern matched: '{pattern}' -> '{match.group()}'")
            return True
    
    print(f"❌ [DETECT_GOODBYE] No goodbye patterns detected in: '{response_text[:100]}...'")
    return False

def check_required_fields_collected(thread_id):
    """
    Check if all required fields have been collected in the conversation
    This ensures the form is complete before triggering extraction and webhook
    
    Args:
        thread_id: The thread ID to check
        
    Returns:
        bool: True if all required fields are collected, False otherwise
    """
    print(f"🔍 [CHECK_REQUIRED_FIELDS] Checking required fields for thread: {thread_id}")
    
    try:
        # Get conversation history
        history = get_conversation_history(thread_id)
        if not history:
            print("❌ [CHECK_REQUIRED_FIELDS] No conversation history found")
            return False
        
        # Combine all conversation text for analysis
        conversation_text = ""
        for message in history:
            role = message['role']
            content = message['content']
            conversation_text += f"{role.upper()}: {content}\n\n"
        
        print(f"📋 [CHECK_REQUIRED_FIELDS] Conversation length: {len(conversation_text)} characters")
        
        # Define required fields and their indicators
        required_fields = {
            'incident_mentioned': [
                'accident', 'crash', 'collision', 'incident', 'wreck', 'hit', 'collided'
            ],
            'date_mentioned': [
                'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october', 'november', 'december',
                'january', 'february', 'yesterday', 'last week', 'last month', 'recently', 'ago',
                '2024', '2023', '2025', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'
            ],
            'location_mentioned': [
                'california', 'texas', 'florida', 'new york', 'los angeles', 'houston', 'miami', 'chicago',
                'phoenix', 'philadelphia', 'san antonio', 'san diego', 'dallas', 'san jose', 'austin',
                'jacksonville', 'fort worth', 'columbus', 'charlotte', 'san francisco', 'indianapolis',
                'seattle', 'denver', 'washington', 'boston', 'el paso', 'nashville', 'detroit', 'oklahoma city',
                'portland', 'las vegas', 'memphis', 'louisville', 'baltimore', 'milwaukee', 'albuquerque',
                'tucson', 'fresno', 'sacramento', 'mesa', 'kansas city', 'atlanta', 'long beach', 'colorado springs',
                'raleigh', 'miami', 'virginia beach', 'omaha', 'oakland', 'minneapolis', 'tulsa', 'arlington',
                'tampa', 'new orleans', 'wichita', 'cleveland', 'bakersfield', 'aurora', 'anaheim', 'honolulu'
            ],
            'injury_mentioned': [
                'hurt', 'injured', 'pain', 'hospital', 'doctor', 'medical', 'ambulance', 'emergency',
                'whiplash', 'broken', 'fracture', 'concussion', 'bruise', 'cut', 'laceration'
            ],
            'contact_info_mentioned': [
                'phone', 'email', 'contact', 'number', '@', 'gmail', 'yahoo', 'hotmail', 'outlook'
            ],
            'name_mentioned': [
                'my name is', 'i am', 'i\'m', 'call me', 'this is'
            ]
        }
        
        # Convert to lowercase for case-insensitive matching
        conversation_lower = conversation_text.lower()
        
        # Check each required field
        fields_found = {}
        for field_name, indicators in required_fields.items():
            found = any(indicator in conversation_lower for indicator in indicators)
            fields_found[field_name] = found
            print(f"🔍 [CHECK_REQUIRED_FIELDS] {field_name}: {'✅ Found' if found else '❌ Missing'}")
        
        # Check if all critical fields are present
        critical_fields = ['incident_mentioned', 'date_mentioned', 'location_mentioned', 'contact_info_mentioned']
        all_critical_present = all(fields_found[field] for field in critical_fields)
        
        # Optional but recommended fields
        recommended_fields = ['injury_mentioned', 'name_mentioned']
        recommended_present = any(fields_found[field] for field in recommended_fields)
        
        # Final decision: All critical fields + at least one recommended field
        all_required_collected = all_critical_present and recommended_present
        
        print(f"📊 [CHECK_REQUIRED_FIELDS] Critical fields: {sum(fields_found[field] for field in critical_fields)}/{len(critical_fields)}")
        print(f"📊 [CHECK_REQUIRED_FIELDS] Recommended fields: {sum(fields_found[field] for field in recommended_fields)}/{len(recommended_fields)}")
        print(f"📊 [CHECK_REQUIRED_FIELDS] All required collected: {'✅ Yes' if all_required_collected else '❌ No'}")
        
        return all_required_collected
        
    except Exception as e:
        print(f"❌ [CHECK_REQUIRED_FIELDS] Error checking required fields: {e}")
        return False

@app.route('/process_message', methods=['POST'])
def process_message():
    """Process chat message with OpenAI and save to MySQL with thread support"""
    print(f"🚀 [PROCESS_MESSAGE] Starting request processing at {datetime.now()}")
    
    try:
        # Log request details (reduced verbosity for performance)
        print(f"📋 [PROCESS_MESSAGE] Request content type: {request.content_type}")
        print(f"📋 [PROCESS_MESSAGE] Request method: {request.method}")
        # Only log headers in debug mode to reduce processing time
        if os.getenv('DEBUG_HEADERS') == 'true':
            print(f"📋 [PROCESS_MESSAGE] Request headers: {dict(request.headers)}")
        
        # Handle JSON, multipart form data, and form-encoded data
        if request.content_type and 'multipart/form-data' in request.content_type:
            print("📋 [PROCESS_MESSAGE] Processing multipart form data")
            # Handle file upload in multipart form
            message = request.form.get('message')
            session_id = request.form.get('session_id', 'default_session')
            thread_id = request.form.get('thread_id')
            file_upload = request.files.get('fileUpload')  # File object
            file_url = request.form.get('fileUrl')  # URL to file
            
            print(f"📋 [PROCESS_MESSAGE] Multipart data - message: {message}, session_id: {session_id}, thread_id: {thread_id}")
            print(f"📋 [PROCESS_MESSAGE] File upload present: {file_upload is not None}")
            print(f"📋 [PROCESS_MESSAGE] File URL present: {file_url is not None}")
            if file_upload:
                print(f"📋 [PROCESS_MESSAGE] File details - name: {file_upload.filename}, content_type: {file_upload.content_type}")
            if file_url:
                print(f"📋 [PROCESS_MESSAGE] File URL: {file_url}")
        elif request.content_type and 'application/x-www-form-urlencoded' in request.content_type:
            print("📋 [PROCESS_MESSAGE] Processing form-encoded data")
            # Debug: Print all form fields to see what CRM is sending
            print(f"📋 [PROCESS_MESSAGE] All form fields: {dict(request.form)}")
            
            # Handle form-encoded data (like from CRM webhooks)
            # Try different possible field names for message
            message = (request.form.get('message') or 
                      request.form.get('Message') or 
                      request.form.get('Body') or 
                      request.form.get('body') or
                      request.form.get('text') or
                      request.form.get('Text') or
                      request.form.get('content') or
                      request.form.get('Content'))
            
            session_id = request.form.get('session_id', 'default_session')
            thread_id = request.form.get('thread_id')
            file_upload = None  # No file uploads in form-encoded data
            file_url = request.form.get('fileUrl')  # URL to file
            
            print(f"📋 [PROCESS_MESSAGE] Form data - message: {message}, session_id: {session_id}, thread_id: {thread_id}")
            print(f"📋 [PROCESS_MESSAGE] File URL present: {file_url is not None}")
            if file_url:
                print(f"📋 [PROCESS_MESSAGE] File URL: {file_url}")
        else:
            print("📋 [PROCESS_MESSAGE] Processing JSON payload")
            # Handle JSON payload
            data = request.json
            message = data.get('message')
            session_id = data.get('session_id', 'default_session')
            thread_id = data.get('thread_id')
            file_upload = None
            file_url = data.get('fileUrl')  # URL to file
            
            print(f"📋 [PROCESS_MESSAGE] JSON data - message: {message}, session_id: {session_id}, thread_id: {thread_id}")
            print(f"📋 [PROCESS_MESSAGE] File URL present: {file_url is not None}")
            if file_url:
                print(f"📋 [PROCESS_MESSAGE] File URL: {file_url}")
        
        # Handle file URL if provided
        if file_url and is_valid_url(file_url):
            print(f"🌐 [PROCESS_MESSAGE] Processing file URL: {file_url}")
            downloaded_file, downloaded_filename, content_type = download_file_from_url(file_url)
            if downloaded_file:
                print(f"✅ [PROCESS_MESSAGE] File downloaded from URL: {downloaded_filename}")
                # Create a file-like object that mimics Flask's file upload
                class DownloadedFile:
                    def __init__(self, file_obj, filename, content_type):
                        self.file = file_obj
                        self.filename = filename
                        self.content_type = content_type
                        self.file.seek(0, 2)  # Seek to end to get size
                        self.size = self.file.tell()
                        self.file.seek(0)  # Reset to beginning
                    def seek(self, offset, whence=0):
                        return self.file.seek(offset, whence)
                    def tell(self):
                        return self.file.tell()
                    def read(self, size=None):
                        return self.file.read(size)
                file_upload = DownloadedFile(downloaded_file, downloaded_filename, content_type)
                print(f"✅ [PROCESS_MESSAGE] Downloaded file object created: {file_upload.filename}, size: {file_upload.size}")
            else:
                print(f"❌ [PROCESS_MESSAGE] Failed to download file from URL: {file_url}")
                return jsonify({'error': f'Failed to download file from URL: {file_url}'}), 400
        
        # Validate that either message, fileUpload, or fileUrl is provided
        print(f"🔍 [PROCESS_MESSAGE] Validation - message present: {bool(message)}, file_upload present: {bool(file_upload)}")
        if not message and not file_upload:
            print("❌ [PROCESS_MESSAGE] Validation failed: Neither message nor fileUpload/fileUrl provided")
            return jsonify({'error': 'Either message, fileUpload, or fileUrl is required'}), 400
        
        print("✅ [PROCESS_MESSAGE] Request validation passed")
        
        # Get or create thread
        print(f"🔄 [PROCESS_MESSAGE] Getting/creating thread for session_id: {session_id}, thread_id: {thread_id}")
        thread_info = get_or_create_thread(session_id, thread_id)
        if not thread_info:
            print("❌ [PROCESS_MESSAGE] Failed to create or retrieve thread")
            return jsonify({'error': 'Failed to create or retrieve thread'}), 500
        
        thread_id = thread_info['thread_id']
        print(f"✅ [PROCESS_MESSAGE] Thread ready: {thread_id}")
        
        # Handle file upload if present
        file_id = None
        extracted_text = None
        if file_upload:
            print(f"📄 [PROCESS_MESSAGE] Starting file processing for: {file_upload.filename}")
            try:
                # Define supported file types (all will use OCR)
                supported_extensions = {'txt', 'pdf', 'doc', 'docx', 'md', 'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'}
                file_extension = file_upload.filename.rsplit('.', 1)[1].lower() if '.' in file_upload.filename else ''
                print(f"📄 [PROCESS_MESSAGE] File extension: {file_extension}")
                if file_extension not in supported_extensions:
                    print(f"❌ [PROCESS_MESSAGE] Unsupported file type: {file_extension}")
                    return jsonify({'error': f'File type not supported. Supported types: {", ".join(supported_extensions)}'}), 400
                # Check file size (max 20MB for OpenAI)
                file_upload.seek(0, 2)  # Seek to end
                file_size = file_upload.tell()
                file_upload.seek(0)  # Reset to beginning
                print(f"📄 [PROCESS_MESSAGE] File size: {file_size} bytes")
                if file_size > 20 * 1024 * 1024:  # 20MB limit
                    print(f"❌ [PROCESS_MESSAGE] File too large: {file_size} bytes")
                    return jsonify({'error': 'File size too large. Maximum size is 20MB'}), 400
                # Process all files using OCR
                print(f"📄 [PROCESS_MESSAGE] Starting OCR text extraction for: {file_upload.filename}")
                # Extract text from file using OCR
                extracted_text = extract_text_from_file(file_upload, file_upload.filename)
                if extracted_text:
                    print(f"✅ [PROCESS_MESSAGE] Text extraction successful: {len(extracted_text)} characters")
                    # SKIP: Uploading extracted text to OpenAI as a file
                    file_id = None  # No file_id for OpenAI
                else:
                    print("❌ [PROCESS_MESSAGE] Text extraction failed")
                    return jsonify({'error': 'Failed to extract text from file. Please ensure the file contains readable text.'}), 400
                print(f"📊 [PROCESS_MESSAGE] File processing complete - size: {file_size} bytes, type: {file_extension}")
                # Save file metadata to database
                print("💾 [PROCESS_MESSAGE] Saving file metadata to database")
                save_file_to_db(file_id, file_upload.filename, file_size, file_extension, thread_id, session_id)
                print("✅ [PROCESS_MESSAGE] File metadata saved to database")
            except Exception as e:
                print(f"❌ [PROCESS_MESSAGE] File upload error: {e}")
                print(f"📄 [PROCESS_MESSAGE] File details - Name: {file_upload.filename}, Size: {file_size}, Type: {file_extension}")
                import traceback
                print(f"📄 [PROCESS_MESSAGE] File error traceback: {traceback.format_exc()}")
                return jsonify({'error': f'Failed to upload file to OpenAI: {str(e)}'}), 500
        
        # Prepare content for database and OpenAI
        print("📝 [PROCESS_MESSAGE] Preparing content for processing")
        if file_upload and extracted_text:
            # For all files, include the extracted text in the user message with clear instructions
            user_content = f"""File uploaded: {file_upload.filename}\n\nExtracted text from file:\n{extracted_text}\n\n{message if message else 'Please analyze this text and provide a clear, professional response without any formatting artifacts or citations.'}\n\nPlease provide a clean, readable response without any source citations or formatting artifacts."""
            print(f"📝 [PROCESS_MESSAGE] Prepared content with file: {len(user_content)} characters")
        else:
            user_content = message if message else f"File uploaded: {file_upload.filename if file_upload else 'Unknown file'}"
            print(f"📝 [PROCESS_MESSAGE] Prepared content without file: {len(user_content)} characters")
        
        # Save user message to database with file information
        print("💾 [PROCESS_MESSAGE] Saving user message to database")
        try:
            save_message_to_db(thread_id, 'user', user_content, None, file_upload.filename if file_upload else None, file_size if file_upload else None)
            print("✅ [PROCESS_MESSAGE] User message saved to database")
        except Exception as e:
            print(f"❌ [PROCESS_MESSAGE] Database operation failed: {e}")
            import traceback
            print(f"📋 [PROCESS_MESSAGE] Database error traceback: {traceback.format_exc()}")
        
        # Use OpenAI Assistants API
        print("🤖 [PROCESS_MESSAGE] Starting OpenAI Assistants API processing")
        try:
            if not assistant_id:
                print("❌ [PROCESS_MESSAGE] OpenAI Assistant ID not configured")
                return jsonify({'error': 'OpenAI Assistant ID not configured'}), 500
            # Get client with beta headers
            openai_client = get_openai_client()
            print(f"🔧 [PROCESS_MESSAGE] OpenAI client created with headers: {openai_client._client.headers.get('OpenAI-Beta', 'NOT SET')}")
            print(f"🔧 [PROCESS_MESSAGE] All headers: {dict(openai_client._client.headers)}")
            # Create or get thread for this conversation
            # Store the original database thread_id for saving responses
            database_thread_id = thread_id
            
            if not thread_id:
                # Create new thread
                print("🆕 [PROCESS_MESSAGE] Creating new OpenAI thread")
                thread = openai_client.beta.threads.create()
                openai_thread_id = thread.id
                print(f"🆕 [PROCESS_MESSAGE] Created new OpenAI thread: {openai_thread_id}")
            else:
                # Check if we have a stored OpenAI thread ID for this database thread
                stored_openai_thread_id = get_openai_thread_id(thread_id)
                
                if stored_openai_thread_id:
                    # Use the stored OpenAI thread ID
                    try:
                        print(f"📋 [PROCESS_MESSAGE] Retrieving stored OpenAI thread: {stored_openai_thread_id}")
                        thread = openai_client.beta.threads.retrieve(stored_openai_thread_id)
                        openai_thread_id = stored_openai_thread_id
                        print(f"📋 [PROCESS_MESSAGE] Retrieved existing OpenAI thread: {openai_thread_id}")
                        
                        # Sync conversation history to OpenAI thread for context continuity
                        print("🔄 [PROCESS_MESSAGE] Syncing conversation history to OpenAI thread for context")
                        sync_conversation_history_to_openai(openai_client, openai_thread_id, database_thread_id)
                        
                    except Exception as e:
                        print(f"⚠️ [PROCESS_MESSAGE] Stored thread {stored_openai_thread_id} not found in OpenAI, creating new one: {e}")
                        # Thread doesn't exist, create new one
                        thread = openai_client.beta.threads.create()
                        openai_thread_id = thread.id
                        print(f"🆕 [PROCESS_MESSAGE] Created new OpenAI thread: {openai_thread_id}")
                        # Store the new mapping
                        get_or_create_openai_thread_mapping(database_thread_id, openai_thread_id)
                        
                        # Sync conversation history to the new thread
                        print("🔄 [PROCESS_MESSAGE] Syncing conversation history to new OpenAI thread")
                        sync_conversation_history_to_openai(openai_client, openai_thread_id, database_thread_id)
                else:
                    # No stored mapping, create new OpenAI thread
                    print(f"🆕 [PROCESS_MESSAGE] No stored OpenAI thread for database thread {thread_id}, creating new one")
                    thread = openai_client.beta.threads.create()
                    openai_thread_id = thread.id
                    print(f"🆕 [PROCESS_MESSAGE] Created new OpenAI thread: {openai_thread_id}")
                    # Store the new mapping
                    get_or_create_openai_thread_mapping(database_thread_id, openai_thread_id)
                    
                    # Sync conversation history to the new thread
                    print("🔄 [PROCESS_MESSAGE] Syncing conversation history to new OpenAI thread")
                    sync_conversation_history_to_openai(openai_client, openai_thread_id, database_thread_id)
            # Only send the user_content as the message, do not attach files
            print("💬 [PROCESS_MESSAGE] Creating text-only message (no file attachments)")
            openai_client.beta.threads.messages.create(
                thread_id=openai_thread_id,
                role="user",
                content=user_content
            )
            print("✅ [PROCESS_MESSAGE] Text message created")
            
            # Run the assistant with optimized settings for faster responses
            print(f"🤖 [PROCESS_MESSAGE] Starting assistant run with assistant_id: {assistant_id}")
            run = openai_client.beta.threads.runs.create(
                thread_id=openai_thread_id,
                assistant_id=assistant_id,
                # Add instructions to keep responses concise and ensure proper goodbye detection
                instructions="Please provide a concise, helpful response. Keep it brief but informative. IMPORTANT: When ending a conversation, always end with 'Goodbye and Take Care' to ensure proper conversation closure."
            )
            print(f"🤖 [PROCESS_MESSAGE] Assistant run started: {run.id}")
            
            # Wait for the run to complete with optimized polling
            print("⏳ [PROCESS_MESSAGE] Waiting for assistant run to complete")
            import time
            max_wait_time = 20  # Reduced from 30 to 20 seconds
            start_time = time.time()
            poll_count = 0
            
            while True:
                run_status = openai_client.beta.threads.runs.retrieve(
                    thread_id=openai_thread_id,
                    run_id=run.id
                )
                
                poll_count += 1
                # Only log every 3rd poll to reduce log noise
                if poll_count % 3 == 0:
                    print(f"⏳ [PROCESS_MESSAGE] Run status: {run_status.status}")
                
                if run_status.status == 'completed':
                    print("✅ [PROCESS_MESSAGE] Assistant run completed")
                    break
                elif run_status.status == 'failed':
                    print(f"❌ [PROCESS_MESSAGE] Assistant run failed: {run_status.last_error}")
                    raise Exception(f"Assistant run failed: {run_status.last_error}")
                elif run_status.status == 'requires_action':
                    print(f"⚠️ [PROCESS_MESSAGE] Assistant requires action: {run_status.required_action}")
                    raise Exception("Assistant requires action")
                elif run_status.status == 'expired':
                    print(f"❌ [PROCESS_MESSAGE] Assistant run expired")
                    raise Exception("Assistant run expired")
                
                # Check for timeout
                elapsed_time = time.time() - start_time
                if elapsed_time > max_wait_time:
                    print(f"❌ [PROCESS_MESSAGE] Assistant run timed out after {max_wait_time} seconds")
                    raise Exception(f"Assistant run timed out after {max_wait_time} seconds")
                
                # Faster polling for quicker responses
                time.sleep(0.3)  # Reduced from 0.5 to 0.3 seconds
            
            # Get the assistant's response
            print("📋 [PROCESS_MESSAGE] Retrieving assistant response")
            messages = openai_client.beta.threads.messages.list(thread_id=openai_thread_id)
            assistant_response = messages.data[0].content[0].text.value
            print(f"📋 [PROCESS_MESSAGE] Raw assistant response length: {len(assistant_response)}")
            
            # Clean up the response to remove formatting artifacts and citations
            print("🧹 [PROCESS_MESSAGE] Cleaning assistant response")
            assistant_response = clean_response_text(assistant_response)
            print(f"🧹 [PROCESS_MESSAGE] Cleaned response length: {len(assistant_response)}")
            
        except Exception as e:
            print(f"❌ [PROCESS_MESSAGE] OpenAI Assistants API error: {e}")
            print(f"❌ [PROCESS_MESSAGE] Error type: {type(e)}")
            print(f"❌ [PROCESS_MESSAGE] Error details: {str(e)}")
            import traceback
            print(f"❌ [PROCESS_MESSAGE] OpenAI error traceback: {traceback.format_exc()}")
            return jsonify({'error': f'Failed to get response from OpenAI Assistant: {str(e)}'}), 500
        
        # Save assistant response to database using the original database thread_id
        print("💾 [PROCESS_MESSAGE] Saving assistant response to database")
        try:
            save_message_to_db(database_thread_id, 'assistant', assistant_response, None, None, None)
            print("✅ [PROCESS_MESSAGE] Assistant response saved to database")
        except Exception as e:
            print(f"❌ [PROCESS_MESSAGE] Failed to save assistant response to database: {e}")
            import traceback
            print(f"❌ [PROCESS_MESSAGE] Database save error traceback: {traceback.format_exc()}")
        
        # Initialize response data first
        response_data = {
            'response': assistant_response,
            'session_id': session_id,
            'thread_id': database_thread_id,
            'timestamp': datetime.now().isoformat()
        }
        
        # Check for goodbye detection and trigger validator assistant
        print("🔍 [PROCESS_MESSAGE] Checking for goodbye detection")
        goodbye_triggered = detect_goodbye_message(assistant_response)
        
        if goodbye_triggered:
            print("👋 [PROCESS_MESSAGE] Goodbye detected! Checking if all required fields are collected")
            
            # Check if all required fields are present before proceeding
            required_fields_collected = check_required_fields_collected(database_thread_id)
            
            if required_fields_collected:
                print("✅ [PROCESS_MESSAGE] All required fields collected, proceeding with extraction")
                try:
                    # Extract incident details using validator assistant
                    incident_details = extract_incident_details_with_gpt(database_thread_id)
                    
                    if incident_details:
                        print("✅ [PROCESS_MESSAGE] Incident details extracted successfully")
                        
                        # Save incident details to database
                        save_incident_details(database_thread_id, incident_details)
                        print("💾 [PROCESS_MESSAGE] Incident details saved to database")
                        
                        # Send to RPA webhook
                        send_to_rpa_webhook(database_thread_id, incident_details)
                        print("🌐 [PROCESS_MESSAGE] Data sent to RPA webhook")
                        
                        # Add extraction status to response
                        response_data['incident_extraction'] = 'completed'
                        response_data['incident_details'] = incident_details
                    else:
                        print("⚠️ [PROCESS_MESSAGE] Failed to extract incident details")
                        response_data['incident_extraction'] = 'failed'
                except Exception as e:
                    print(f"❌ [PROCESS_MESSAGE] Error during incident extraction: {e}")
                    response_data['incident_extraction'] = 'error'
                    response_data['extraction_error'] = str(e)
            else:
                print("⚠️ [PROCESS_MESSAGE] Required fields not collected, skipping extraction and webhook")
                response_data['incident_extraction'] = 'skipped'
                response_data['extraction_reason'] = 'Required fields not collected'
        else:
            print("💬 [PROCESS_MESSAGE] No goodbye detected, continuing conversation")
        
        # Add file information if a file was uploaded
        if file_id:
            response_data['file_uploaded'] = True
            response_data['file_id'] = file_id
            response_data['filename'] = file_upload.filename if file_upload else 'Unknown'
        
        print(f"✅ [PROCESS_MESSAGE] Request processing completed successfully at {datetime.now()}")
        print(f"📊 [PROCESS_MESSAGE] Response data keys: {list(response_data.keys())}")
        
        return jsonify(response_data), 200
        
    except Exception as e:
        print(f"❌ [PROCESS_MESSAGE] Unexpected error processing message: {e}")
        import traceback
        print(f"❌ [PROCESS_MESSAGE] Unexpected error traceback: {traceback.format_exc()}")
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
            elif not validator_assistant_id:
                openai_status = "unhealthy - Missing Validator Assistant ID"
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

@app.route('/test-url-download', methods=['POST'])
def test_url_download():
    """Test endpoint for URL file download functionality"""
    try:
        data = request.json
        if not data or 'url' not in data:
            return jsonify({'error': 'URL is required in JSON body'}), 400
        
        url = data['url']
        print(f"🌐 [TEST_URL_DOWNLOAD] Testing URL download: {url}")
        
        if not is_valid_url(url):
            return jsonify({'error': 'Invalid URL format'}), 400
        
        # Download the file
        downloaded_file, filename, content_type = download_file_from_url(url)
        
        if not downloaded_file:
            return jsonify({
                'success': False,
                'error': 'Failed to download file from URL',
                'url': url
            }), 400
        
        # Test file processing
        try:
            extracted_text = extract_text_from_file(downloaded_file, filename)
            
            if extracted_text:
                print(f"✅ [TEST_URL_DOWNLOAD] Text extraction successful: {len(extracted_text)} characters")
            else:
                return jsonify({
                    'success': False,
                    'error': 'Text extraction failed for downloaded file',
                    'url': url,
                    'filename': filename,
                    'content_type': content_type
                }), 500
            
            return jsonify({
                'success': True,
                'message': 'URL file download and processing test successful',
                'url': url,
                'filename': filename,
                'content_type': content_type,
                'extracted_text_length': len(extracted_text),
                'timestamp': datetime.now().isoformat()
            }), 200
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'File processing test failed: {str(e)}',
                'url': url,
                'filename': filename,
                'content_type': content_type
            }), 500
        
    except Exception as e:
        return jsonify({'error': f'Test failed: {str(e)}'}), 500

def download_file_from_url(url, max_size_mb=20):
    """
    Download a file from a URL and return it as a file-like object
    
    Args:
        url: The URL to download the file from
        max_size_mb: Maximum file size in MB (default 20MB)
        
    Returns:
        tuple: (file_obj, filename, content_type) or (None, None, None) if failed
    """
    print(f"🌐 [DOWNLOAD_FILE_FROM_URL] Starting download from URL: {url}")
    
    try:
        # Validate URL format
        parsed_url = urlparse(url)
        if not parsed_url.scheme or not parsed_url.netloc:
            print("❌ [DOWNLOAD_FILE_FROM_URL] Invalid URL format")
            return None, None, None
        
        # Get filename from URL
        filename = os.path.basename(parsed_url.path)
        if not filename:
            # If no filename in URL, try to get it from Content-Disposition header
            filename = "downloaded_file"
        
        print(f"🌐 [DOWNLOAD_FILE_FROM_URL] Filename from URL: {filename}")
        
        # Download file with streaming to check size
        print("🌐 [DOWNLOAD_FILE_FROM_URL] Starting download...")
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        
        # Check content type
        content_type = response.headers.get('content-type', '')
        print(f"🌐 [DOWNLOAD_FILE_FROM_URL] Content type: {content_type}")
        
        # Check file size
        content_length = response.headers.get('content-length')
        if content_length:
            file_size = int(content_length)
            max_size_bytes = max_size_mb * 1024 * 1024
            if file_size > max_size_bytes:
                print(f"❌ [DOWNLOAD_FILE_FROM_URL] File too large: {file_size} bytes (max: {max_size_bytes})")
                return None, None, None
            print(f"🌐 [DOWNLOAD_FILE_FROM_URL] File size: {file_size} bytes")
        
        # Download the file content
        file_content = response.content
        print(f"🌐 [DOWNLOAD_FILE_FROM_URL] Downloaded {len(file_content)} bytes")
        
        # Create file-like object
        file_obj = io.BytesIO(file_content)
        file_obj.name = filename
        
        print(f"✅ [DOWNLOAD_FILE_FROM_URL] File downloaded successfully: {filename}")
        return file_obj, filename, content_type
        
    except requests.exceptions.RequestException as e:
        print(f"❌ [DOWNLOAD_FILE_FROM_URL] Download failed: {e}")
        return None, None, None
    except Exception as e:
        print(f"❌ [DOWNLOAD_FILE_FROM_URL] Unexpected error: {e}")
        import traceback
        print(f"❌ [DOWNLOAD_FILE_FROM_URL] Error traceback: {traceback.format_exc()}")
        return None, None, None

def is_valid_url(url):
    """
    Check if a string is a valid URL
    
    Args:
        url: String to check
        
    Returns:
        bool: True if valid URL, False otherwise
    """
    try:
        parsed = urlparse(url)
        return bool(parsed.scheme and parsed.netloc)
    except:
        return False

def create_incident_details_table():
    """Create the incident_details table if it doesn't exist"""
    connection = get_mysql_connection()
    if not connection:
        return False
    
    try:
        cursor = connection.cursor()
        
        # Create incident_details table with updated schema
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS incident_details (
                id INT AUTO_INCREMENT PRIMARY KEY,
                thread_id VARCHAR(255) NOT NULL,
                date_of_incident VARCHAR(50),
                month_name VARCHAR(20),
                day INT,
                year INT,
                zip_code VARCHAR(10),
                was_accident_my_fault ENUM('true', 'false'),
                was_issued_ticket ENUM('true', 'false'),
                physically_injured ENUM('true', 'false'),
                ambulance_called ENUM('true', 'false'),
                went_to_emergency_room ENUM('true', 'false'),
                injury_types TEXT,
                attorney_helping ENUM('true', 'false'),
                attorney_rejected ENUM('true', 'false'),
                significant_property_damage ENUM('high', 'moderate', 'minor', 'i_dont_know'),
                state_of_injury VARCHAR(100),
                city_of_injury VARCHAR(100),
                other_party_vehicle_type ENUM('personal', 'work', 'taxi'),
                injury_description TEXT,
                first_name VARCHAR(100),
                last_name VARCHAR(100),
                phone_number VARCHAR(20),
                email VARCHAR(255),
                consent_given ENUM('true', 'false'),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_thread_id (thread_id)
            )
        """)
        
        # Add new columns if they don't exist (for existing tables)
        try:
            cursor.execute("ALTER TABLE incident_details ADD COLUMN month_name VARCHAR(20)")
            print("✅ [CREATE_INCIDENT_DETAILS_TABLE] Added month_name column")
        except Exception as e:
            if "Duplicate column name" in str(e):
                print("ℹ️ [CREATE_INCIDENT_DETAILS_TABLE] month_name column already exists")
            else:
                print(f"⚠️ [CREATE_INCIDENT_DETAILS_TABLE] Error adding month_name: {e}")
        
        try:
            cursor.execute("ALTER TABLE incident_details ADD COLUMN zip_code VARCHAR(10)")
            print("✅ [CREATE_INCIDENT_DETAILS_TABLE] Added zip_code column")
        except Exception as e:
            if "Duplicate column name" in str(e):
                print("ℹ️ [CREATE_INCIDENT_DETAILS_TABLE] zip_code column already exists")
            else:
                print(f"⚠️ [CREATE_INCIDENT_DETAILS_TABLE] Error adding zip_code: {e}")
        
        # Update ENUM values for existing columns - handle transition from yes/no to true/false
        try:
            # First, clear existing data to avoid conflicts
            cursor.execute("DELETE FROM incident_details")
            print("✅ [CREATE_INCIDENT_DETAILS_TABLE] Cleared existing data to avoid ENUM conflicts")
            
            # Now update the ENUM definitions
            cursor.execute("ALTER TABLE incident_details MODIFY COLUMN was_accident_my_fault ENUM('true', 'false')")
            cursor.execute("ALTER TABLE incident_details MODIFY COLUMN was_issued_ticket ENUM('true', 'false')")
            cursor.execute("ALTER TABLE incident_details MODIFY COLUMN physically_injured ENUM('true', 'false')")
            cursor.execute("ALTER TABLE incident_details MODIFY COLUMN ambulance_called ENUM('true', 'false')")
            cursor.execute("ALTER TABLE incident_details MODIFY COLUMN went_to_emergency_room ENUM('true', 'false')")
            cursor.execute("ALTER TABLE incident_details MODIFY COLUMN attorney_helping ENUM('true', 'false')")
            cursor.execute("ALTER TABLE incident_details MODIFY COLUMN attorney_rejected ENUM('true', 'false')")
            cursor.execute("ALTER TABLE incident_details MODIFY COLUMN consent_given ENUM('true', 'false')")
            cursor.execute("ALTER TABLE incident_details MODIFY COLUMN significant_property_damage ENUM('high', 'moderate', 'minor', 'i_dont_know')")
            cursor.execute("ALTER TABLE incident_details MODIFY COLUMN other_party_vehicle_type ENUM('personal', 'work', 'taxi')")
            print("✅ [CREATE_INCIDENT_DETAILS_TABLE] Updated ENUM definitions to true/false")
        except Exception as e:
            print(f"⚠️ [CREATE_INCIDENT_DETAILS_TABLE] Error updating ENUM values: {e}")
        
        connection.commit()
        cursor.close()
        connection.close()
        print("✅ [CREATE_INCIDENT_DETAILS_TABLE] Table created successfully")
        return True
        
    except Error as e:
        print(f"❌ [CREATE_INCIDENT_DETAILS_TABLE] Error creating table: {e}")
        return False

def extract_incident_details_with_gpt(thread_id):
    """
    Use VALIDATOR_ASSISTANT to extract incident details from conversation history
    
    Args:
        thread_id: The thread ID to extract details from
        
    Returns:
        dict: Extracted incident details or None if extraction fails
    """
    print(f"🔍 [EXTRACT_INCIDENT_DETAILS] Starting extraction for thread: {thread_id}")
    
    try:
        # Check if validator assistant is configured
        if not validator_assistant_id:
            print("❌ [EXTRACT_INCIDENT_DETAILS] Validator Assistant ID not configured")
            return None
        
        # Get conversation history
        history = get_conversation_history(thread_id)
        if not history:
            print("❌ [EXTRACT_INCIDENT_DETAILS] No conversation history found")
            return None
        
        # Prepare conversation text for validator assistant analysis
        conversation_text = ""
        for message in history:
            role = message['role']
            content = message['content']
            conversation_text += f"{role.upper()}: {content}\n\n"
        
        print(f"📋 [EXTRACT_INCIDENT_DETAILS] Conversation length: {len(conversation_text)} characters")
        
        # Create OpenAI client
        openai_client = get_openai_client()
        
        # Create a new thread for the validator assistant
        print("🆕 [EXTRACT_INCIDENT_DETAILS] Creating validator assistant thread")
        validator_thread = openai_client.beta.threads.create()
        print(f"🆕 [EXTRACT_INCIDENT_DETAILS] Created validator thread: {validator_thread.id}")
        
        # Add the conversation as a message to the validator thread
        print("📝 [EXTRACT_INCIDENT_DETAILS] Adding conversation to validator thread")
        openai_client.beta.threads.messages.create(
            thread_id=validator_thread.id,
            role="user",
            content=conversation_text
        )
        print("✅ [EXTRACT_INCIDENT_DETAILS] Conversation added to validator thread")
        
        # Run the validator assistant
        print(f"🤖 [EXTRACT_INCIDENT_DETAILS] Starting validator assistant run with ID: {validator_assistant_id}")
        run = openai_client.beta.threads.runs.create(
            thread_id=validator_thread.id,
            assistant_id=validator_assistant_id
        )
        print(f"🤖 [EXTRACT_INCIDENT_DETAILS] Validator assistant run started: {run.id}")
        
        # Wait for the run to complete
        print("⏳ [EXTRACT_INCIDENT_DETAILS] Waiting for validator assistant to complete")
        import time
        max_wait_time = 60  # Increased to 60 seconds for complex conversations
        start_time = time.time()
        
        while True:
            run_status = openai_client.beta.threads.runs.retrieve(
                thread_id=validator_thread.id,
                run_id=run.id
            )
            
            print(f"⏳ [EXTRACT_INCIDENT_DETAILS] Validator run status: {run_status.status}")
            
            if run_status.status == 'completed':
                print("✅ [EXTRACT_INCIDENT_DETAILS] Validator assistant run completed")
                break
            elif run_status.status == 'failed':
                print(f"❌ [EXTRACT_INCIDENT_DETAILS] Validator assistant run failed: {run_status.last_error}")
                raise Exception(f"Validator assistant run failed: {run_status.last_error}")
            elif run_status.status == 'requires_action':
                print(f"⚠️ [EXTRACT_INCIDENT_DETAILS] Validator assistant requires action: {run_status.required_action}")
                raise Exception("Validator assistant requires action")
            elif run_status.status == 'expired':
                print(f"❌ [EXTRACT_INCIDENT_DETAILS] Validator assistant run expired")
                raise Exception("Validator assistant run expired")
            
            # Check for timeout
            elapsed_time = time.time() - start_time
            if elapsed_time > max_wait_time:
                print(f"❌ [EXTRACT_INCIDENT_DETAILS] Validator assistant run timed out after {max_wait_time} seconds")
                raise Exception(f"Validator assistant run timed out after {max_wait_time} seconds")
            
            time.sleep(0.5)  # Poll every 0.5 seconds
        
        # Get the validator assistant's response
        print("📋 [EXTRACT_INCIDENT_DETAILS] Retrieving validator assistant response")
        messages = openai_client.beta.threads.messages.list(thread_id=validator_thread.id)
        validator_response = messages.data[0].content[0].text.value
        print(f"📋 [EXTRACT_INCIDENT_DETAILS] Raw validator response length: {len(validator_response)}")
        
        # Clean up the response to remove formatting artifacts
        print("🧹 [EXTRACT_INCIDENT_DETAILS] Cleaning validator response")
        validator_response = clean_response_text(validator_response)
        print(f"🧹 [EXTRACT_INCIDENT_DETAILS] Cleaned response length: {len(validator_response)}")
        
        # Try to parse JSON
        try:
            import json
            incident_details = json.loads(validator_response)
            print(f"✅ [EXTRACT_INCIDENT_DETAILS] Successfully extracted {len(incident_details)} fields using validator assistant")
            return incident_details
        except json.JSONDecodeError as e:
            print(f"❌ [EXTRACT_INCIDENT_DETAILS] Failed to parse JSON response: {e}")
            print(f"❌ [EXTRACT_INCIDENT_DETAILS] Raw response: {validator_response}")
            return None
            
    except Exception as e:
        print(f"❌ [EXTRACT_INCIDENT_DETAILS] Extraction failed: {e}")
        import traceback
        print(f"❌ [EXTRACT_INCIDENT_DETAILS] Error traceback: {traceback.format_exc()}")
        return None

def save_incident_details(thread_id, incident_details):
    """Save extracted incident details to database"""
    print(f"💾 [SAVE_INCIDENT_DETAILS] Saving details for thread: {thread_id}")
    
    # Debug: Print all incident details to see what values we're getting
    print(f"🔍 [SAVE_INCIDENT_DETAILS] Incident details: {json.dumps(incident_details, indent=2)}")
    
    # Validate and convert boolean values to ensure they match ENUM definitions
    boolean_fields = [
        'was_accident_my_fault', 'was_issued_ticket', 'physically_injured',
        'ambulance_called', 'went_to_emergency_room', 'attorney_helping',
        'attorney_rejected', 'consent_given'
    ]
    
    for field in boolean_fields:
        value = incident_details.get(field)
        if value is not None:
            if value in ['true', 'false']:
                print(f"✅ [SAVE_INCIDENT_DETAILS] {field}: {value} (valid)")
            elif value in ['yes', 'no']:
                # Convert yes/no to true/false
                converted_value = 'true' if value == 'yes' else 'false'
                incident_details[field] = converted_value
                print(f"🔄 [SAVE_INCIDENT_DETAILS] {field}: {value} -> {converted_value} (converted)")
            elif value == 'null':
                incident_details[field] = None
                print(f"🔄 [SAVE_INCIDENT_DETAILS] {field}: {value} -> None (converted)")
            else:
                print(f"⚠️ [SAVE_INCIDENT_DETAILS] {field}: {value} (unknown value, setting to None)")
                incident_details[field] = None
    
    connection = get_mysql_connection()
    if not connection:
        return False
    
    try:
        cursor = connection.cursor()
        
        # Check if record exists
        cursor.execute("SELECT id FROM incident_details WHERE thread_id = %s", (thread_id,))
        existing_record = cursor.fetchone()
        
        if existing_record:
            # Update existing record
            print("🔄 [SAVE_INCIDENT_DETAILS] Updating existing record")
            cursor.execute("""
                UPDATE incident_details SET
                    date_of_incident = %s,
                    month_name = %s,
                    day = %s,
                    year = %s,
                    zip_code = %s,
                    was_accident_my_fault = %s,
                    was_issued_ticket = %s,
                    physically_injured = %s,
                    ambulance_called = %s,
                    went_to_emergency_room = %s,
                    injury_types = %s,
                    attorney_helping = %s,
                    attorney_rejected = %s,
                    significant_property_damage = %s,
                    state_of_injury = %s,
                    city_of_injury = %s,
                    other_party_vehicle_type = %s,
                    injury_description = %s,
                    first_name = %s,
                    last_name = %s,
                    phone_number = %s,
                    email = %s,
                    consent_given = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE thread_id = %s
            """, (
                incident_details.get('date_of_incident'),
                incident_details.get('month_name'),
                incident_details.get('day'),
                incident_details.get('year'),
                incident_details.get('zip_code'),
                incident_details.get('was_accident_my_fault'),
                incident_details.get('was_issued_ticket'),
                incident_details.get('physically_injured'),
                incident_details.get('ambulance_called'),
                incident_details.get('went_to_emergency_room'),
                json.dumps(incident_details.get('injury_types', [])),
                incident_details.get('attorney_helping'),
                incident_details.get('attorney_rejected'),
                incident_details.get('significant_property_damage'),
                incident_details.get('state_of_injury'),
                incident_details.get('city_of_injury'),
                incident_details.get('other_party_vehicle_type'),
                incident_details.get('injury_description'),
                incident_details.get('first_name'),
                incident_details.get('last_name'),
                incident_details.get('phone_number'),
                incident_details.get('email'),
                incident_details.get('consent_given'),
                thread_id
            ))
        else:
            # Insert new record
            print("🆕 [SAVE_INCIDENT_DETAILS] Creating new record")
            cursor.execute("""
                INSERT INTO incident_details (
                    thread_id, date_of_incident, month_name, day, year, zip_code,
                    was_accident_my_fault, was_issued_ticket, physically_injured,
                    ambulance_called, went_to_emergency_room, injury_types,
                    attorney_helping, attorney_rejected, significant_property_damage,
                    state_of_injury, city_of_injury, other_party_vehicle_type,
                    injury_description, first_name, last_name, phone_number,
                    email, consent_given
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """, (
                thread_id,
                incident_details.get('date_of_incident'),
                incident_details.get('month_name'),
                incident_details.get('day'),
                incident_details.get('year'),
                incident_details.get('zip_code'),
                incident_details.get('was_accident_my_fault'),
                incident_details.get('was_issued_ticket'),
                incident_details.get('physically_injured'),
                incident_details.get('ambulance_called'),
                incident_details.get('went_to_emergency_room'),
                json.dumps(incident_details.get('injury_types', [])),
                incident_details.get('attorney_helping'),
                incident_details.get('attorney_rejected'),
                incident_details.get('significant_property_damage'),
                incident_details.get('state_of_injury'),
                incident_details.get('city_of_injury'),
                incident_details.get('other_party_vehicle_type'),
                incident_details.get('injury_description'),
                incident_details.get('first_name'),
                incident_details.get('last_name'),
                incident_details.get('phone_number'),
                incident_details.get('email'),
                incident_details.get('consent_given')
            ))
        
        connection.commit()
        cursor.close()
        connection.close()
        print("✅ [SAVE_INCIDENT_DETAILS] Details saved successfully")
        return True
        
    except Error as e:
        print(f"❌ [SAVE_INCIDENT_DETAILS] Database error: {e}")
        return False

def get_incident_details(thread_id):
    """Get incident details for a thread"""
    print(f"🔍 [GET_INCIDENT_DETAILS] Retrieving details for thread: {thread_id}")
    
    connection = get_mysql_connection()
    if not connection:
        return None
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT * FROM incident_details WHERE thread_id = %s
        """, (thread_id,))
        
        result = cursor.fetchone()
        cursor.close()
        connection.close()
        
        if result:
            # Parse injury_types JSON
            if result.get('injury_types'):
                try:
                    result['injury_types'] = json.loads(result['injury_types'])
                except:
                    result['injury_types'] = []
            else:
                result['injury_types'] = []
            
            print(f"✅ [GET_INCIDENT_DETAILS] Found details for thread: {thread_id}")
            return result
        else:
            print(f"⚠️ [GET_INCIDENT_DETAILS] No details found for thread: {thread_id}")
            return None
            
    except Error as e:
        print(f"❌ [GET_INCIDENT_DETAILS] Database error: {e}")
        return None

def send_to_rpa_webhook(thread_id, incident_details):
    """Send incident details to RPA webhook"""
    webhook_url = os.getenv('RPA_WEBHOOK_URL') or os.getenv('RPA_WEBHOOK')
    if not webhook_url:
        print("⚠️ [RPA_WEBHOOK] No webhook URL configured")
        return False
    
    print(f"🌐 [RPA_WEBHOOK] Sending data to webhook: {webhook_url}")
    
    try:
        # Convert string boolean values to actual booleans for webhook
        webhook_incident_details = {}
        for key, value in incident_details.items():
            if key in ['was_accident_my_fault', 'was_issued_ticket', 'physically_injured', 
                      'ambulance_called', 'went_to_emergency_room', 'attorney_helping', 
                      'attorney_rejected', 'consent_given']:
                if value == 'true':
                    webhook_incident_details[key] = True
                elif value == 'false':
                    webhook_incident_details[key] = False
                else:
                    # For null/unknown values, default to False instead of None
                    webhook_incident_details[key] = False
                    print(f"🔄 [RPA_WEBHOOK] {key}: {value} -> False (default for null/unknown)")
            else:
                webhook_incident_details[key] = value
        
        # Add zip code from incident_details to top level
        zip_code = incident_details.get('zip_code', '')
        
        payload = {
            "form_data": {
                "thread_id": thread_id,
                "timestamp": datetime.now().isoformat(),
                "zip": zip_code,
                "incident_details": webhook_incident_details,
                "submit_form": False  # Always false as requested
            }
        }
        
        print(f"🔍 [RPA_WEBHOOK] Payload being sent: {json.dumps(payload, indent=2)}")
        
        response = requests.post(
            webhook_url,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        if response.status_code == 200:
            print("✅ [RPA_WEBHOOK] Data sent successfully")
            return True
        else:
            print(f"❌ [RPA_WEBHOOK] Webhook returned status {response.status_code}")
            print(f"❌ [RPA_WEBHOOK] Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ [RPA_WEBHOOK] Failed to send data: {e}")
        return False

@app.route('/incident-details/<thread_id>', methods=['GET'])
def get_incident_details_endpoint(thread_id):
    """Get incident details for a thread"""
    try:
        details = get_incident_details(thread_id)
        
        if details:
            return jsonify({
                'thread_id': thread_id,
                'incident_details': details,
                'extracted_at': details.get('created_at'),
                'updated_at': details.get('updated_at')
            }), 200
        else:
            return jsonify({
                'error': 'No incident details found for this thread'
            }), 404
            
    except Exception as e:
        print(f"❌ [GET_INCIDENT_DETAILS_ENDPOINT] Error: {e}")
        return jsonify({'error': 'Failed to get incident details'}), 500

@app.route('/incident-details/<thread_id>', methods=['POST'])
def extract_incident_details_endpoint(thread_id):
    """Extract incident details for a thread"""
    try:
        print(f"🎯 [EXTRACT_INCIDENT_DETAILS_ENDPOINT] Starting extraction for thread: {thread_id}")
        
        # Extract details using VALIDATOR_ASSISTANT
        incident_details = extract_incident_details_with_gpt(thread_id)
        
        if not incident_details:
            return jsonify({
                'error': 'Failed to extract incident details'
            }), 500
        
        # Save to database
        if not save_incident_details(thread_id, incident_details):
            return jsonify({
                'error': 'Failed to save incident details'
            }), 500
        
        # Send to RPA webhook if configured
        send_to_rpa_webhook(thread_id, incident_details)
        
        return jsonify({
            'thread_id': thread_id,
            'incident_details': incident_details,
            'extracted_at': datetime.now().isoformat(),
            'message': 'Incident details extracted successfully'
        }), 200
        
    except Exception as e:
        print(f"❌ [EXTRACT_INCIDENT_DETAILS_ENDPOINT] Error: {e}")
        return jsonify({'error': 'Failed to extract incident details'}), 500

# Initialize incident details table when app starts
print("🔧 Initializing incident details table...")
incident_table_thread = threading.Thread(target=create_incident_details_table, daemon=True)
incident_table_thread.start()

# This module is designed to be imported by start.py
# The Flask app will be started by the startup script 