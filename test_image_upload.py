#!/usr/bin/env python3
"""
Test script for image upload and OCR functionality
"""

import requests
import json
import os
from PIL import Image, ImageDraw, ImageFont

def create_test_file():
    """Create a test file with text for OCR testing"""
    # Create a white image
    img = Image.new('RGB', (600, 200), color='white')
    draw = ImageDraw.Draw(img)
    
    # Add text to the image
    try:
        font = ImageFont.load_default()
    except:
        font = None
    
    # Add multiple lines of text
    text_lines = [
        "Test Document for OCR",
        "This is sample text that should be extracted",
        "from this file using Tesseract OCR.",
        "The chatbot should be able to analyze this text."
    ]
    
    y_position = 20
    for line in text_lines:
        draw.text((20, y_position), line, fill='black', font=font)
        y_position += 30
    
    # Save the test file
    test_file_path = "test_ocr_document.png"
    img.save(test_file_path)
    print(f"✅ Created test file: {test_file_path}")
    return test_file_path

def test_file_upload(base_url):
    """Test file upload and OCR processing"""
    print("\n🔍 Testing file upload and OCR...")
    
    # Create test file
    test_file_path = create_test_file()
    
    try:
        # Test file upload
        with open(test_file_path, 'rb') as file_obj:
            files = {'fileUpload': file_obj}
            data = {
                'message': 'Please analyze the text extracted from this file',
                'session_id': 'test_ocr_session',
                'thread_id': None
            }
            
            response = requests.post(f"{base_url}/process_message", files=files, data=data)
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ File upload successful!")
                print(f"Response: {json.dumps(result, indent=2)}")
                return result.get('thread_id')
            else:
                print(f"❌ File upload failed: {response.text}")
                return None
                
    finally:
        # Clean up test file
        if os.path.exists(test_file_path):
            os.remove(test_file_path)
            print(f"🧹 Cleaned up test file")

def main():
    """Run file upload tests"""
    base_url = "http://localhost:5007"
    
    print("🚀 Starting file upload and OCR tests...")
    
    # Test file upload
    thread_id = test_file_upload(base_url)
    
    if thread_id:
        print(f"✅ File upload test completed successfully with thread_id: {thread_id}")
    else:
        print("❌ File upload test failed")

if __name__ == "__main__":
    main() 