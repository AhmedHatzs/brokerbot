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
    
    # OpenAI Configuration (REQUIRED - from environment)
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    OPENAI_ASSISTANT_ID = os.getenv('OPENAI_ASSISTANT_ID')
    
    # OpenAI Model Settings (hardcoded defaults)
    OPENAI_MODEL = 'gpt-3.5-turbo'
    OPENAI_MAX_TOKENS = 1000
    OPENAI_TEMPERATURE = 0.7
    
    # Conversation Memory Configuration (hardcoded)
    MAX_TOKENS_PER_CHUNK = 2000
    MAX_CONTEXT_TOKENS = 4000
    SESSION_TIMEOUT_HOURS = 24
    
    # Storage Configuration (hardcoded)
    STORAGE_TYPE = 'mysql'  # 'file', 'memory', or 'mysql'
    STORAGE_DIR = 'conversations'
    
    # MySQL Database Configuration (from environment)
    MYSQL_HOST = os.getenv('MYSQL_HOST')
    MYSQL_PORT = int(os.getenv('MYSQL_PORT', '3306'))
    MYSQL_DATABASE = os.getenv('MYSQL_DATABASE')
    MYSQL_USER = os.getenv('MYSQL_USER')
    MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD')
    MYSQL_SSL_MODE = os.getenv('MYSQL_SSL_MODE', 'REQUIRED')
    
    # Server Configuration (hardcoded)
    PORT = 5001
    HOST = '0.0.0.0'
    DEBUG = False
    
    # Bot Configuration (hardcoded)
    BOT_NAME = 'BrokerBot'
    BOT_PERSONALITY = 'You are a helpful AI assistant named BrokerBot. You are knowledgeable, friendly, and always try to provide accurate and helpful responses.'
    
    @classmethod
    def validate_config(cls):
        """Validate that required configuration is present"""
        errors = []
        
        # Check for required API key and assistant ID
        if not cls.OPENAI_API_KEY:
            errors.append("OPENAI_API_KEY environment variable is required")
        
        if not cls.OPENAI_ASSISTANT_ID:
            errors.append("OPENAI_ASSISTANT_ID environment variable is required")
        
        # Check for MySQL configuration if using MySQL storage
        if cls.STORAGE_TYPE == 'mysql':
            if not cls.MYSQL_HOST:
                errors.append("MYSQL_HOST environment variable is required for MySQL storage")
            if not cls.MYSQL_DATABASE:
                errors.append("MYSQL_DATABASE environment variable is required for MySQL storage")
            if not cls.MYSQL_USER:
                errors.append("MYSQL_USER environment variable is required for MySQL storage")
            if not cls.MYSQL_PASSWORD:
                errors.append("MYSQL_PASSWORD environment variable is required for MySQL storage")
        
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
        if cls.STORAGE_TYPE == 'mysql':
            print(f"   • MySQL Database: {cls.MYSQL_DATABASE}")
            print(f"   • MySQL Host: {cls.MYSQL_HOST}")
            print(f"   • MySQL Port: {cls.MYSQL_PORT}")
        print(f"   • Bot Name: {cls.BOT_NAME}")
        print(f"   • API Key: {'✅ Set' if cls.OPENAI_API_KEY else '❌ Missing'}")
        print(f"   • Debug Mode: {cls.DEBUG}")
        print(f"   • Port: {cls.PORT}")
        print(f"   • Host: {cls.HOST}") 