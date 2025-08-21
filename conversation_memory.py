#!/usr/bin/env python3
"""
BrokerBot Conversation Memory System
Handles conversation history with chunking for long conversations
"""

import json
import os
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from abc import ABC, abstractmethod


@dataclass
class Message:
    """Represents a single message in a conversation"""
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: datetime
    token_count: Optional[int] = None
    
    def to_dict(self) -> Dict:
        """Convert message to dictionary for serialization"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Message':
        """Create message from dictionary"""
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


@dataclass
class ConversationChunk:
    """Represents a chunk of conversation history"""
    chunk_id: str
    messages: List[Message]
    total_tokens: int
    created_at: datetime
    summary: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert chunk to dictionary for serialization"""
        return {
            'chunk_id': self.chunk_id,
            'messages': [msg.to_dict() for msg in self.messages],
            'total_tokens': self.total_tokens,
            'created_at': self.created_at.isoformat(),
            'summary': self.summary
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ConversationChunk':
        """Create chunk from dictionary"""
        return cls(
            chunk_id=data['chunk_id'],
            messages=[Message.from_dict(msg) for msg in data['messages']],
            total_tokens=data['total_tokens'],
            created_at=datetime.fromisoformat(data['created_at']),
            summary=data.get('summary')
        )


class ConversationStorage(ABC):
    """Abstract base class for conversation storage implementations"""
    
    @abstractmethod
    def save_session(self, session_id: str, conversation_data: Dict) -> None:
        """Save conversation data for a session"""
        pass
    
    @abstractmethod
    def load_session(self, session_id: str) -> Optional[Dict]:
        """Load conversation data for a session"""
        pass
    
    @abstractmethod
    def delete_session(self, session_id: str) -> bool:
        """Delete conversation data for a session"""
        pass
    
    @abstractmethod
    def list_sessions(self) -> List[str]:
        """List all session IDs"""
        pass


class InMemoryStorage(ConversationStorage):
    """In-memory storage for conversation data"""
    
    def __init__(self):
        self.sessions: Dict[str, Dict] = {}
    
    def save_session(self, session_id: str, conversation_data: Dict) -> None:
        """Save conversation data in memory"""
        self.sessions[session_id] = conversation_data
    
    def load_session(self, session_id: str) -> Optional[Dict]:
        """Load conversation data from memory"""
        return self.sessions.get(session_id)
    
    def delete_session(self, session_id: str) -> bool:
        """Delete conversation data from memory"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False
    
    def list_sessions(self) -> List[str]:
        """List all session IDs in memory"""
        return list(self.sessions.keys())


class FileStorage(ConversationStorage):
    """File-based storage for conversation data"""
    
    def __init__(self, storage_dir: str = "conversations"):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)
    
    def _get_session_path(self, session_id: str) -> str:
        """Get file path for a session"""
        return os.path.join(self.storage_dir, f"{session_id}.json")
    
    def save_session(self, session_id: str, conversation_data: Dict) -> None:
        """Save conversation data to file"""
        try:
            with open(self._get_session_path(session_id), 'w') as f:
                json.dump(conversation_data, f, indent=2, default=str)
        except Exception as e:
            print(f"❌ Error saving session {session_id}: {e}")
    
    def load_session(self, session_id: str) -> Optional[Dict]:
        """Load conversation data from file"""
        try:
            session_path = self._get_session_path(session_id)
            if os.path.exists(session_path):
                with open(session_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"❌ Error loading session {session_id}: {e}")
        return None
    
    def delete_session(self, session_id: str) -> bool:
        """Delete conversation data file"""
        try:
            session_path = self._get_session_path(session_id)
            if os.path.exists(session_path):
                os.remove(session_path)
                return True
        except Exception as e:
            print(f"❌ Error deleting session {session_id}: {e}")
        return False
    
    def list_sessions(self) -> List[str]:
        """List all session IDs from files"""
        try:
            files = [f for f in os.listdir(self.storage_dir) if f.endswith('.json')]
            return [f.replace('.json', '') for f in files]
        except Exception as e:
            print(f"❌ Error listing sessions: {e}")
            return []


class ConversationMemory:
    """
    Main conversation memory manager with chunking capabilities
    
    This class handles:
    - Session management with unique IDs
    - Conversation chunking based on token limits
    - Message storage and retrieval
    - Context window management for LLMs
    """
    
    def __init__(
        self,
        storage: ConversationStorage,
        max_tokens_per_chunk: int = 2000,
        max_context_tokens: int = 4000,
        session_timeout_hours: int = 24
    ):
        self.storage = storage
        self.max_tokens_per_chunk = max_tokens_per_chunk
        self.max_context_tokens = max_context_tokens
        self.session_timeout_hours = session_timeout_hours
    
    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text
        Simple estimation: ~4 characters per token
        """
        return len(text) // 4 + 1
    
    def create_session(self) -> str:
        """Create a new conversation session"""
        session_id = str(uuid.uuid4())
        session_data = {
            'session_id': session_id,
            'created_at': datetime.now().isoformat(),
            'last_activity': datetime.now().isoformat(),
            'chunks': [],
            'current_messages': [],
            'total_messages': 0
        }
        self.storage.save_session(session_id, session_data)
        return session_id
    
    def add_message(self, session_id: str, role: str, content: str) -> bool:
        """
        Add a message to the conversation
        
        Args:
            session_id: The session identifier
            role: 'user' or 'assistant'
            content: The message content
            
        Returns:
            bool: True if message was added successfully
        """
        try:
            # Load session data
            session_data = self.storage.load_session(session_id)
            if not session_data:
                return False
            
            # Create new message
            message = Message(
                role=role,
                content=content,
                timestamp=datetime.now(),
                token_count=self.estimate_tokens(content)
            )
            
            # Add to current messages
            current_messages = [Message.from_dict(msg) for msg in session_data.get('current_messages', [])]
            current_messages.append(message)
            
            # Check if chunking is needed
            total_tokens = sum(msg.token_count or 0 for msg in current_messages)
            
            if total_tokens > self.max_tokens_per_chunk:
                # Create a new chunk from current messages (except the last one)
                chunk_messages = current_messages[:-1]
                chunk = ConversationChunk(
                    chunk_id=str(uuid.uuid4()),
                    messages=chunk_messages,
                    total_tokens=sum(msg.token_count or 0 for msg in chunk_messages),
                    created_at=datetime.now()
                )
                
                # Add chunk to session
                chunks = session_data.get('chunks', [])
                chunks.append(chunk.to_dict())
                
                # Keep only the latest message in current_messages
                current_messages = [message]
                
                print(f"📦 Created conversation chunk with {len(chunk_messages)} messages ({chunk.total_tokens} tokens)")
            
            # Update session data
            session_data.update({
                'last_activity': datetime.now().isoformat(),
                'chunks': session_data.get('chunks', []),
                'current_messages': [msg.to_dict() for msg in current_messages],
                'total_messages': session_data.get('total_messages', 0) + 1
            })
            
            # Save updated session
            self.storage.save_session(session_id, session_data)
            return True
            
        except Exception as e:
            print(f"❌ Error adding message to session {session_id}: {e}")
            return False
    
    def get_conversation_context(self, session_id: str, include_chunks: int = 2) -> List[Dict]:
        """
        Get conversation context for LLM
        
        Args:
            session_id: The session identifier
            include_chunks: Number of recent chunks to include
            
        Returns:
            List of message dictionaries formatted for LLM
        """
        try:
            session_data = self.storage.load_session(session_id)
            if not session_data:
                return []
            
            context_messages = []
            total_tokens = 0
            
            # Add recent chunks (summarized if available)
            chunks = session_data.get('chunks', [])
            recent_chunks = chunks[-include_chunks:] if include_chunks > 0 else []
            
            for chunk_data in recent_chunks:
                chunk = ConversationChunk.from_dict(chunk_data)
                
                if chunk.summary:
                    # Use summary if available
                    context_messages.append({
                        'role': 'system',
                        'content': f"Previous conversation summary: {chunk.summary}"
                    })
                    total_tokens += self.estimate_tokens(chunk.summary)
                else:
                    # Include recent messages from chunk if within token limit
                    for msg in chunk.messages[-5:]:  # Last 5 messages from chunk
                        if total_tokens + (msg.token_count or 0) <= self.max_context_tokens:
                            context_messages.append({
                                'role': msg.role,
                                'content': msg.content
                            })
                            total_tokens += msg.token_count or 0
                        else:
                            break
            
            # Add current messages
            current_messages = [Message.from_dict(msg) for msg in session_data.get('current_messages', [])]
            for msg in current_messages:
                if total_tokens + (msg.token_count or 0) <= self.max_context_tokens:
                    context_messages.append({
                        'role': msg.role,
                        'content': msg.content
                    })
                    total_tokens += msg.token_count or 0
                else:
                    break
            
            return context_messages
            
        except Exception as e:
            print(f"❌ Error getting context for session {session_id}: {e}")
            return []
    
    def get_session_info(self, session_id: str) -> Optional[Dict]:
        """Get session information and statistics"""
        try:
            session_data = self.storage.load_session(session_id)
            if not session_data:
                return None
            
            chunks = session_data.get('chunks', [])
            current_messages = session_data.get('current_messages', [])
            
            return {
                'session_id': session_id,
                'created_at': session_data.get('created_at'),
                'last_activity': session_data.get('last_activity'),
                'total_messages': session_data.get('total_messages', 0),
                'total_chunks': len(chunks),
                'current_messages_count': len(current_messages),
                'estimated_total_tokens': sum(
                    chunk.get('total_tokens', 0) for chunk in chunks
                ) + sum(
                    self.estimate_tokens(msg.get('content', '')) for msg in current_messages
                )
            }
            
        except Exception as e:
            print(f"❌ Error getting session info for {session_id}: {e}")
            return None
    
    def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions"""
        try:
            expired_count = 0
            cutoff_time = datetime.now() - timedelta(hours=self.session_timeout_hours)
            
            for session_id in self.storage.list_sessions():
                session_data = self.storage.load_session(session_id)
                if session_data:
                    last_activity = datetime.fromisoformat(session_data.get('last_activity', ''))
                    if last_activity < cutoff_time:
                        self.storage.delete_session(session_id)
                        expired_count += 1
            
            if expired_count > 0:
                print(f"🧹 Cleaned up {expired_count} expired sessions")
            
            return expired_count
            
        except Exception as e:
            print(f"❌ Error cleaning up expired sessions: {e}")
            return 0 