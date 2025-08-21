#!/usr/bin/env python3
"""
BrokerBot MySQL Storage Implementation
Handles conversation data storage in MySQL database
"""

import json
import mysql.connector
from mysql.connector import Error
from typing import List, Dict, Optional
from datetime import datetime
from conversation_memory import ConversationStorage
import logging

logger = logging.getLogger(__name__)

class MySQLStorage(ConversationStorage):
    """MySQL-based storage for conversation data"""
    
    def __init__(self, host: str, port: int, database: str, user: str, password: str, ssl_mode: str = 'REQUIRED'):
        """
        Initialize MySQL storage
        
        Args:
            host: Database host
            port: Database port
            database: Database name
            user: Database username
            password: Database password
            ssl_mode: SSL mode for connection (REQUIRED, DISABLED, etc.)
        """
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.ssl_mode = ssl_mode
        
        # Initialize database tables
        self._init_database()
    
    def _get_connection(self):
        """Get MySQL database connection"""
        try:
            # Configure SSL based on ssl_mode
            ssl_config = {}
            if self.ssl_mode == 'REQUIRED':
                ssl_config = {
                    'ssl_disabled': False,
                    'ssl_verify_cert': False,  # Disable certificate verification for cloud databases
                    'ssl_verify_identity': False
                }
            elif self.ssl_mode == 'DISABLED':
                ssl_config = {
                    'ssl_disabled': True
                }
            elif self.ssl_mode == 'PREFERRED':
                ssl_config = {
                    'ssl_disabled': False,
                    'ssl_verify_cert': False
                }
            
            connection = mysql.connector.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
                autocommit=True,
                **ssl_config
            )
            return connection
        except Error as e:
            logger.error(f"Error connecting to MySQL: {e}")
            raise
    
    def _init_database(self):
        """Initialize database tables if they don't exist"""
        try:
            connection = self._get_connection()
            cursor = connection.cursor()
            
            # Create sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversation_sessions (
                    session_id VARCHAR(255) PRIMARY KEY,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    total_messages INT DEFAULT 0,
                    total_chunks INT DEFAULT 0,
                    current_messages_count INT DEFAULT 0,
                    estimated_total_tokens INT DEFAULT 0
                )
            """)
            
            # Create chunks table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversation_chunks (
                    chunk_id VARCHAR(255) PRIMARY KEY,
                    session_id VARCHAR(255),
                    messages JSON,
                    total_tokens INT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    summary TEXT,
                    FOREIGN KEY (session_id) REFERENCES conversation_sessions(session_id) ON DELETE CASCADE
                )
            """)
            
            # Create current messages table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS current_messages (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    session_id VARCHAR(255),
                    role VARCHAR(50),
                    content TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    token_count INT,
                    FOREIGN KEY (session_id) REFERENCES conversation_sessions(session_id) ON DELETE CASCADE
                )
            """)
            
            connection.commit()
            cursor.close()
            connection.close()
            
            logger.info("MySQL database tables initialized successfully")
            
        except Error as e:
            logger.error(f"Error initializing database: {e}")
            raise
    
    def save_session(self, session_id: str, conversation_data: Dict) -> None:
        """Save conversation data to MySQL"""
        try:
            connection = self._get_connection()
            cursor = connection.cursor()
            
            # Extract data from conversation_data
            created_at = conversation_data.get('created_at')
            last_activity = conversation_data.get('last_activity')
            total_messages = conversation_data.get('total_messages', 0)
            chunks = conversation_data.get('chunks', [])
            current_messages = conversation_data.get('current_messages', [])
            
            # Calculate statistics
            total_chunks = len(chunks)
            current_messages_count = len(current_messages)
            estimated_total_tokens = sum(
                chunk.get('total_tokens', 0) for chunk in chunks
            ) + sum(
                self._estimate_tokens(msg.get('content', '')) for msg in current_messages
            )
            
            # Insert or update session
            cursor.execute("""
                INSERT INTO conversation_sessions 
                (session_id, created_at, last_activity, total_messages, total_chunks, current_messages_count, estimated_total_tokens)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                last_activity = VALUES(last_activity),
                total_messages = VALUES(total_messages),
                total_chunks = VALUES(total_chunks),
                current_messages_count = VALUES(current_messages_count),
                estimated_total_tokens = VALUES(estimated_total_tokens)
            """, (
                session_id, created_at, last_activity, total_messages, 
                total_chunks, current_messages_count, estimated_total_tokens
            ))
            
            # Clear existing chunks and current messages
            cursor.execute("DELETE FROM conversation_chunks WHERE session_id = %s", (session_id,))
            cursor.execute("DELETE FROM current_messages WHERE session_id = %s", (session_id,))
            
            # Insert chunks
            for chunk_data in chunks:
                cursor.execute("""
                    INSERT INTO conversation_chunks 
                    (chunk_id, session_id, messages, total_tokens, created_at, summary)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    chunk_data['chunk_id'],
                    session_id,
                    json.dumps(chunk_data['messages']),
                    chunk_data['total_tokens'],
                    chunk_data['created_at'],
                    chunk_data.get('summary')
                ))
            
            # Insert current messages
            for msg_data in current_messages:
                cursor.execute("""
                    INSERT INTO current_messages 
                    (session_id, role, content, timestamp, token_count)
                    VALUES (%s, %s, %s, %s, %s)
                """, (
                    session_id,
                    msg_data['role'],
                    msg_data['content'],
                    msg_data['timestamp'],
                    msg_data.get('token_count')
                ))
            
            connection.commit()
            cursor.close()
            connection.close()
            
        except Error as e:
            logger.error(f"Error saving session {session_id}: {e}")
            raise
    
    def load_session(self, session_id: str) -> Optional[Dict]:
        """Load conversation data from MySQL"""
        try:
            connection = self._get_connection()
            cursor = connection.cursor(dictionary=True)
            
            # Get session data
            cursor.execute("""
                SELECT * FROM conversation_sessions WHERE session_id = %s
            """, (session_id,))
            
            session_row = cursor.fetchone()
            if not session_row:
                return None
            
            # Get chunks
            cursor.execute("""
                SELECT * FROM conversation_chunks WHERE session_id = %s ORDER BY created_at
            """, (session_id,))
            
            chunks = []
            for chunk_row in cursor.fetchall():
                chunks.append({
                    'chunk_id': chunk_row['chunk_id'],
                    'messages': json.loads(chunk_row['messages']),
                    'total_tokens': chunk_row['total_tokens'],
                    'created_at': chunk_row['created_at'].isoformat(),
                    'summary': chunk_row['summary']
                })
            
            # Get current messages
            cursor.execute("""
                SELECT * FROM current_messages WHERE session_id = %s ORDER BY timestamp
            """, (session_id,))
            
            current_messages = []
            for msg_row in cursor.fetchall():
                current_messages.append({
                    'role': msg_row['role'],
                    'content': msg_row['content'],
                    'timestamp': msg_row['timestamp'].isoformat(),
                    'token_count': msg_row['token_count']
                })
            
            cursor.close()
            connection.close()
            
            return {
                'session_id': session_row['session_id'],
                'created_at': session_row['created_at'].isoformat(),
                'last_activity': session_row['last_activity'].isoformat(),
                'total_messages': session_row['total_messages'],
                'chunks': chunks,
                'current_messages': current_messages
            }
            
        except Error as e:
            logger.error(f"Error loading session {session_id}: {e}")
            return None
    
    def delete_session(self, session_id: str) -> bool:
        """Delete conversation data from MySQL"""
        try:
            connection = self._get_connection()
            cursor = connection.cursor()
            
            # Delete session (cascades to chunks and messages)
            cursor.execute("DELETE FROM conversation_sessions WHERE session_id = %s", (session_id,))
            
            affected_rows = cursor.rowcount
            connection.commit()
            cursor.close()
            connection.close()
            
            return affected_rows > 0
            
        except Error as e:
            logger.error(f"Error deleting session {session_id}: {e}")
            return False
    
    def list_sessions(self) -> List[str]:
        """List all session IDs from MySQL"""
        try:
            connection = self._get_connection()
            cursor = connection.cursor()
            
            cursor.execute("SELECT session_id FROM conversation_sessions")
            sessions = [row[0] for row in cursor.fetchall()]
            
            cursor.close()
            connection.close()
            
            return sessions
            
        except Error as e:
            logger.error(f"Error listing sessions: {e}")
            return []
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for text"""
        return len(text) // 4 + 1 