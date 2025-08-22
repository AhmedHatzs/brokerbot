#!/usr/bin/env python3
"""
Railway-specific database connection test
This script should be run on Railway to test the connection from their environment
"""

import os
import mysql.connector
from mysql.connector import Error
import socket
import requests

def get_railway_info():
    """Get Railway-specific information"""
    print("🚂 Railway Environment Information")
    print("=" * 40)
    
    # Get Railway environment variables
    railway_env = os.getenv('RAILWAY_ENVIRONMENT', 'Not set')
    port = os.getenv('PORT', 'Not set')
    host = os.getenv('HOST', 'Not set')
    
    print(f"Railway Environment: {railway_env}")
    print(f"Port: {port}")
    print(f"Host: {host}")
    
    # Try to get external IP
    try:
        response = requests.get('https://api.ipify.org?format=json', timeout=5)
        external_ip = response.json()['ip']
        print(f"External IP: {external_ip}")
    except:
        print("External IP: Could not determine")
    
    print()

def test_mysql_connection():
    """Test MySQL connection from Railway environment"""
    print("🔍 Testing MySQL Connection from Railway...")
    print("=" * 50)
    
    # Get environment variables
    host = os.getenv('MYSQL_HOST')
    port = os.getenv('MYSQL_PORT', '3306')
    database = os.getenv('MYSQL_DATABASE')
    user = os.getenv('MYSQL_USER')
    password = os.getenv('MYSQL_PASSWORD')
    
    print(f"Host: {host}")
    print(f"Port: {port}")
    print(f"Database: {database}")
    print(f"User: {user}")
    print(f"Password: {'*' * len(password) if password else 'NOT SET'}")
    print()
    
    # Test network connectivity
    print(f"🌐 Testing network connectivity to {host}:{port}...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        result = sock.connect_ex((host, int(port)))
        sock.close()
        
        if result == 0:
            print("✅ Network connectivity: SUCCESS")
        else:
            print(f"❌ Network connectivity: FAILED (Error code: {result})")
            print("💡 This means Railway cannot reach your Aiven Cloud database")
            print("💡 You need to update Aiven Cloud security settings to allow Railway IPs")
            return False
    except Exception as e:
        print(f"❌ Network connectivity test failed: {e}")
        return False
    
    # Test MySQL connection with different SSL modes
    ssl_modes = [
        ("REQUIRED", {"ssl_ca": None, "ssl_verify_cert": True}),
        ("DISABLED", {"ssl_disabled": True}),
        ("PREFERRED", {"ssl_ca": None, "ssl_verify_cert": False})
    ]
    
    for ssl_name, ssl_config in ssl_modes:
        print(f"\n🔄 Testing SSL Mode: {ssl_name}")
        print("-" * 30)
        
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
                
                cursor.close()
                connection.close()
                print(f"✅ Connection successful! Use MYSQL_SSL_MODE={ssl_name}")
                return True
                
        except Error as e:
            print(f"❌ Failed with SSL Mode {ssl_name}: {e}")
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
    
    print("\n❌ All connection attempts failed")
    return False

if __name__ == "__main__":
    get_railway_info()
    success = test_mysql_connection()
    
    if not success:
        print("\n💡 Next Steps:")
        print("1. Go to your Aiven Cloud console")
        print("2. Find your MySQL service")
        print("3. Go to Security/Access Control settings")
        print("4. Add 0.0.0.0/0 to allowed IPs (temporarily)")
        print("5. Or add Railway's specific IP ranges")
        print("6. Redeploy your Railway app")
        exit(1)
    else:
        print("\n🎉 Database connection successful!")
        print("Your Railway app should now work with the database!") 