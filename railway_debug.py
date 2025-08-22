#!/usr/bin/env python3
"""
Railway Deployment Debug Script
Helps troubleshoot 502 gateway errors and deployment issues
"""

import os
import sys
import requests
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_environment_variables():
    """Check if all required environment variables are set"""
    print("🔍 Checking environment variables...")
    
    required_vars = [
        'OPENAI_API_KEY',
        'MYSQL_HOST',
        'MYSQL_PORT',
        'MYSQL_DATABASE',
        'MYSQL_USER',
        'MYSQL_PASSWORD'
    ]
    
    missing_vars = []
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing_vars.append(var)
            print(f"❌ {var}: Not set")
        else:
            # Mask sensitive values
            if 'PASSWORD' in var or 'KEY' in var:
                print(f"✅ {var}: {'*' * min(len(value), 8)}...")
            else:
                print(f"✅ {var}: {value}")
    
    if missing_vars:
        print(f"\n⚠️  Missing {len(missing_vars)} environment variables")
        return False
    else:
        print("\n✅ All required environment variables are set")
        return True

def test_local_server():
    """Test if the local server is running"""
    print("\n🔍 Testing local server...")
    
    port = os.getenv('PORT', '5007')
    base_url = f"http://localhost:{port}"
    
    endpoints = [
        ('/', 'Root endpoint'),
        ('/ping', 'Ping endpoint'),
        ('/health', 'Health endpoint'),
        ('/test-db', 'Database test endpoint')
    ]
    
    for endpoint, description in endpoints:
        try:
            url = f"{base_url}{endpoint}"
            print(f"📡 Testing {description} ({url})...")
            
            response = requests.get(url, timeout=10)
            print(f"✅ {description}: {response.status_code} - {response.text[:100]}...")
            
        except requests.exceptions.ConnectionError:
            print(f"❌ {description}: Connection refused (server not running)")
        except requests.exceptions.Timeout:
            print(f"❌ {description}: Timeout")
        except Exception as e:
            print(f"❌ {description}: {e}")

def test_railway_deployment():
    """Test Railway deployment if URL is provided"""
    railway_url = os.getenv('RAILWAY_URL')
    
    if not railway_url:
        print("\n⚠️  RAILWAY_URL not set - skipping Railway deployment test")
        return
    
    print(f"\n🔍 Testing Railway deployment at {railway_url}...")
    
    endpoints = [
        ('/', 'Root endpoint'),
        ('/ping', 'Ping endpoint'),
        ('/health', 'Health endpoint')
    ]
    
    for endpoint, description in endpoints:
        try:
            url = f"{railway_url}{endpoint}"
            print(f"📡 Testing {description} ({url})...")
            
            response = requests.get(url, timeout=30)
            print(f"✅ {description}: {response.status_code}")
            if response.status_code == 200:
                print(f"   Response: {response.text[:200]}...")
            else:
                print(f"   Error: {response.text}")
                
        except requests.exceptions.Timeout:
            print(f"❌ {description}: Timeout (502 Gateway Error likely)")
        except Exception as e:
            print(f"❌ {description}: {e}")

def main():
    print("=" * 60)
    print("🚗 RAILWAY DEPLOYMENT DEBUG TOOL")
    print("=" * 60)
    
    # Check environment variables
    env_ok = check_environment_variables()
    
    # Test local server if running
    test_local_server()
    
    # Test Railway deployment
    test_railway_deployment()
    
    print("\n" + "=" * 60)
    print("📋 TROUBLESHOOTING TIPS")
    print("=" * 60)
    
    if not env_ok:
        print("1. ❌ Fix missing environment variables in Railway dashboard")
    
    print("2. 🔍 Check Railway logs for startup errors")
    print("3. 🌐 Verify your Railway URL is correct")
    print("4. 🗄️  Check database connectivity (Aiven Cloud settings)")
    print("5. 🔑 Verify OpenAI API key is valid")
    print("6. ⏱️  Wait 2-3 minutes after deployment for full startup")
    
    print("\n🔧 Common 502 Error Causes:")
    print("   - Database connection timeout")
    print("   - Missing environment variables")
    print("   - Application crash during startup")
    print("   - Port configuration issues")
    print("   - Memory/CPU limits exceeded")

if __name__ == "__main__":
    main() 