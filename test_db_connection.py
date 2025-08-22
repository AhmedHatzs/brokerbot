#!/usr/bin/env python3
"""
Database connection test script for Railway deployment
Use this to debug MySQL connection issues
"""

import os
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
import socket

# Load environment variables
load_dotenv()

def test_network_connectivity(host, port):
    """Test basic network connectivity to the database host"""
    print(f"🌐 Testing network connectivity to {host}:{port}...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        result = sock.connect_ex((host, int(port)))
        sock.close()
        
        if result == 0:
            print("✅ Network connectivity: SUCCESS")
            return True
        else:
            print(f"❌ Network connectivity: FAILED (Error code: {result})")
            return False
    except Exception as e:
        print(f"❌ Network connectivity test failed: {e}")
        return False

def test_mysql_connection():
    """Test MySQL connection with detailed error reporting"""
    print("🔍 Testing MySQL Connection...")
    print("=" * 50)
    
    # Get environment variables
    host = os.getenv('MYSQL_HOST')
    port = os.getenv('MYSQL_PORT', '3306')
    database = os.getenv('MYSQL_DATABASE')
    user = os.getenv('MYSQL_USER')
    password = os.getenv('MYSQL_PASSWORD')
    ssl_mode = os.getenv('MYSQL_SSL_MODE', 'REQUIRED')
    
    print(f"Host: {host}")
    print(f"Port: {port}")
    print(f"Database: {database}")
    print(f"User: {user}")
    print(f"SSL Mode: {ssl_mode}")
    print(f"Password: {'*' * len(password) if password else 'NOT SET'}")
    print()
    
    # Test network connectivity first
    if not test_network_connectivity(host, int(port)):
        print("\n💡 Network connectivity failed. This could be due to:")
        print("1. Firewall blocking the connection")
        print("2. Database server not accepting external connections")
        print("3. Incorrect host/port configuration")
        print("4. Aiven Cloud security group settings")
        return False
    
    # Test different SSL configurations
    ssl_configs = [
        ("REQUIRED", {"ssl_ca": None, "ssl_verify_cert": True}),
        ("VERIFY_IDENTITY", {"ssl_ca": None, "ssl_verify_cert": True, "ssl_verify_identity": True}),
        ("DISABLED", {"ssl_disabled": True}),
        ("PREFERRED", {"ssl_ca": None, "ssl_verify_cert": False})
    ]
    
    for ssl_name, ssl_config in ssl_configs:
        print(f"\n🔄 Testing SSL Mode: {ssl_name}")
        print("-" * 30)
        
        # Build connection config
        config = {
            'host': host,
            'port': int(port),
            'database': database,
            'user': user,
            'password': password,
            'connect_timeout': 30,
            'autocommit': True,
            'charset': 'utf8mb4',
            'collation': 'utf8mb4_unicode_ci'
        }
        
        # Add SSL configuration
        config.update(ssl_config)
        
        try:
            connection = mysql.connector.connect(**config)
            
            if connection.is_connected():
                db_info = connection.get_server_info()
                print(f"✅ SUCCESS with SSL Mode: {ssl_name}")
                print(f"✅ Connected to MySQL Server version {db_info}")
                
                cursor = connection.cursor()
                cursor.execute("SELECT DATABASE();")
                record = cursor.fetchone()
                print(f"📊 Connected to database: {record[0]}")
                
                # Test a simple query
                cursor.execute("SELECT 1 as test")
                result = cursor.fetchone()
                print(f"✅ Test query successful: {result[0]}")
                
                cursor.close()
                connection.close()
                print(f"✅ Connection test completed successfully with SSL Mode: {ssl_name}!")
                
                # Update environment variable for the working SSL mode
                print(f"\n💡 Set MYSQL_SSL_MODE={ssl_name} in your Railway environment variables")
                return True
                
        except Error as e:
            print(f"❌ Failed with SSL Mode {ssl_name}: {e}")
            print(f"   Error Code: {e.errno}")
            print(f"   SQL State: {e.sqlstate}")
        except Exception as e:
            print(f"❌ Unexpected error with SSL Mode {ssl_name}: {e}")
    
    print("\n❌ All SSL configurations failed")
    print("\n💡 Troubleshooting Tips:")
    print("1. Check if MYSQL_HOST, MYSQL_PORT, MYSQL_DATABASE, MYSQL_USER, MYSQL_PASSWORD are set")
    print("2. Verify the database server is accessible from Railway")
    print("3. Check Aiven Cloud security group settings - ensure Railway IPs are allowed")
    print("4. Ensure the database user has proper permissions")
    print("5. Check if the database exists")
    print("6. Try connecting from a different network to isolate the issue")
    return False

if __name__ == "__main__":
    success = test_mysql_connection()
    if not success:
        exit(1) 