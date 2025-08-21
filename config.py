#!/usr/bin/env python3
"""
BrokerBot Configuration
Handles environment variables and configuration settings
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Configuration class for BrokerBot"""
    
    # OpenAI Configuration
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    OPENAI_ASSISTANT_ID = os.getenv('OPENAI_ASSISTANT_ID')
    OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')
    OPENAI_MAX_TOKENS = int(os.getenv('OPENAI_MAX_TOKENS', '1000'))
    OPENAI_TEMPERATURE = float(os.getenv('OPENAI_TEMPERATURE', '0.7'))
    
    # Conversation Memory Configuration
    MAX_TOKENS_PER_CHUNK = int(os.getenv('MAX_TOKENS_PER_CHUNK', '2000'))
    MAX_CONTEXT_TOKENS = int(os.getenv('MAX_CONTEXT_TOKENS', '4000'))
    SESSION_TIMEOUT_HOURS = int(os.getenv('SESSION_TIMEOUT_HOURS', '24'))
    
    # Storage Configuration
    STORAGE_TYPE = os.getenv('STORAGE_TYPE', 'file')  # 'file' or 'memory'
    STORAGE_DIR = os.getenv('STORAGE_DIR', 'conversations')
    
    # Server Configuration
    PORT = int(os.getenv('PORT', '5001'))
    HOST = os.getenv('HOST', '0.0.0.0')
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    
    # Bot Configuration
    BOT_NAME = os.getenv('BOT_NAME', 'BrokerBot')
    BOT_PERSONALITY = os.getenv('BOT_PERSONALITY', 'You are a helpful AI assistant.')
    
    @classmethod
    def validate_config(cls):
        """Validate that required configuration is present"""
        errors = []
        
        # Check for required API key and assistant ID
        if not cls.OPENAI_API_KEY:
            errors.append("OPENAI_API_KEY environment variable is required")
        
        if not cls.OPENAI_ASSISTANT_ID:
            errors.append("OPENAI_ASSISTANT_ID environment variable is required")
        
        # Validate numeric values
        if cls.OPENAI_MAX_TOKENS <= 0:
            errors.append("OPENAI_MAX_TOKENS must be greater than 0")
        
        if cls.MAX_TOKENS_PER_CHUNK <= 0:
            errors.append("MAX_TOKENS_PER_CHUNK must be greater than 0")
        
        if cls.MAX_CONTEXT_TOKENS <= 0:
            errors.append("MAX_CONTEXT_TOKENS must be greater than 0")
        
        if cls.SESSION_TIMEOUT_HOURS <= 0:
            errors.append("SESSION_TIMEOUT_HOURS must be greater than 0")
        
        return errors
    
    @classmethod
    def print_config(cls):
        """Print current configuration (without sensitive data)"""
        print("🔧 BrokerBot Configuration:")
        print(f"   • OpenAI Model: {cls.OPENAI_MODEL}")
        print(f"   • OpenAI Assistant ID: {cls.OPENAI_ASSISTANT_ID[:8] + '...' if cls.OPENAI_ASSISTANT_ID else '❌ Missing'}")
        print(f"   • Max Tokens: {cls.OPENAI_MAX_TOKENS}")
        print(f"   • Temperature: {cls.OPENAI_TEMPERATURE}")
        print(f"   • Max Tokens/Chunk: {cls.MAX_TOKENS_PER_CHUNK}")
        print(f"   • Max Context Tokens: {cls.MAX_CONTEXT_TOKENS}")
        print(f"   • Session Timeout: {cls.SESSION_TIMEOUT_HOURS} hours")
        print(f"   • Storage Type: {cls.STORAGE_TYPE}")
        print(f"   • Bot Name: {cls.BOT_NAME}")
        print(f"   • API Key: {'✅ Set' if cls.OPENAI_API_KEY else '❌ Missing'}")
        print(f"   • Debug Mode: {cls.DEBUG}")
        print(f"   • Port: {cls.PORT}")
        print(f"   • Host: {cls.HOST}") 