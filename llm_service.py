#!/usr/bin/env python3
"""
BrokerBot LLM Service
Handles OpenAI Assistant API integration for chat responses
"""

import openai
from typing import List, Dict, Optional
from config import Config
import logging
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LLMService:
    """Service for handling LLM interactions using OpenAI Assistant API"""
    
    def __init__(self):
        """Initialize the LLM service with OpenAI client"""
        if not Config.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is required")
        
        if not Config.OPENAI_ASSISTANT_ID:
            raise ValueError("OPENAI_ASSISTANT_ID is required")
        
        self.client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)
        self.assistant_id = Config.OPENAI_ASSISTANT_ID
        self.model = Config.OPENAI_MODEL
        self.max_tokens = Config.OPENAI_MAX_TOKENS
        self.temperature = Config.OPENAI_TEMPERATURE
        self.bot_personality = Config.BOT_PERSONALITY
        
        # Store thread IDs for each session
        self.session_threads = {}
    
    def get_or_create_thread(self, session_id: str) -> str:
        """
        Get or create a thread for a session
        
        Args:
            session_id: The session identifier
            
        Returns:
            str: The thread ID
        """
        if session_id not in self.session_threads:
            try:
                # Create a new thread
                thread = self.client.beta.threads.create()
                self.session_threads[session_id] = thread.id
                logger.info(f"Created new thread {thread.id} for session {session_id}")
            except Exception as e:
                logger.error(f"Failed to create thread for session {session_id}: {e}")
                raise
        
        return self.session_threads[session_id]
    
    def generate_response(self, conversation_context: List[Dict], user_message: str, session_id: str) -> str:
        """
        Generate a response using OpenAI Assistant API
        
        Args:
            conversation_context: List of previous messages in the conversation
            user_message: The current user message
            session_id: The session identifier
            
        Returns:
            str: The generated response
        """
        try:
            # Get or create thread for this session
            thread_id = self.get_or_create_thread(session_id)
            
            # Add the user message to the thread
            message = self.client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=user_message
            )
            
            logger.info(f"Added user message to thread {thread_id}")
            
            # Run the assistant
            run = self.client.beta.threads.runs.create(
                thread_id=thread_id,
                assistant_id=self.assistant_id
            )
            
            logger.info(f"Started assistant run {run.id}")
            
            # Wait for the run to complete
            while True:
                run_status = self.client.beta.threads.runs.retrieve(
                    thread_id=thread_id,
                    run_id=run.id
                )
                
                if run_status.status == 'completed':
                    break
                elif run_status.status == 'failed':
                    logger.error(f"Assistant run failed: {run_status.last_error}")
                    return "I apologize, but I encountered an error while processing your request."
                elif run_status.status == 'expired':
                    logger.error("Assistant run expired")
                    return "I apologize, but the request took too long to process."
                
                # Wait a bit before checking again
                time.sleep(1)
            
            # Get the assistant's response
            messages = self.client.beta.threads.messages.list(thread_id=thread_id)
            
            # Find the latest assistant message
            for msg in messages.data:
                if msg.role == "assistant" and msg.run_id == run.id:
                    # Get the text content from the message
                    if msg.content and len(msg.content) > 0:
                        content = msg.content[0]
                        if hasattr(content, 'text'):
                            response = content.text.value
                            logger.info(f"Generated response: {response[:100]}...")
                            return response
            
            logger.error("No assistant response found")
            return "I apologize, but I didn't receive a response from my assistant."
                
        except openai.AuthenticationError:
            logger.error("OpenAI authentication failed - check your API key")
            return "I apologize, but there's an authentication issue with my AI service."
            
        except openai.RateLimitError:
            logger.error("OpenAI rate limit exceeded")
            return "I'm receiving too many requests right now. Please try again in a moment."
            
        except openai.APIError as e:
            logger.error(f"OpenAI API error: {e}")
            return "I'm experiencing technical difficulties. Please try again later."
            
        except Exception as e:
            logger.error(f"Unexpected error in LLM service: {e}")
            return "I encountered an unexpected error. Please try again."
    
    def test_connection(self) -> bool:
        """
        Test the connection to OpenAI Assistant API
        
        Returns:
            bool: True if connection is successful, False otherwise
        """
        try:
            # Test by retrieving the assistant
            assistant = self.client.beta.assistants.retrieve(self.assistant_id)
            logger.info(f"Successfully connected to assistant: {assistant.name}")
            return True
        except Exception as e:
            logger.error(f"OpenAI Assistant API connection test failed: {e}")
            return False
    
    def get_usage_info(self) -> Dict:
        """
        Get information about the LLM service configuration
        
        Returns:
            Dict: Configuration information
        """
        return {
            "assistant_id": self.assistant_id[:8] + "..." if self.assistant_id else "Not set",
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "bot_personality": self.bot_personality[:100] + "..." if len(self.bot_personality) > 100 else self.bot_personality,
            "active_threads": len(self.session_threads)
        } 