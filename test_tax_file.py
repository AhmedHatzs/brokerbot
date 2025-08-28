#!/usr/bin/env python3
"""
Test script for OCR functionality with tax.png file
"""

import os
import sys
from PIL import Image
import pytesseract

# Import the OCR function from chat_api
sys.path.append('.')
from chat_api import extract_text_from_file

def test_tax_file_ocr():
    """Test OCR extraction from the tax.png file"""
    print("🔍 Testing OCR extraction from tax.png...")
    
    tax_file_path = "tax.png"
    
    if not os.path.exists(tax_file_path):
        print(f"❌ File {tax_file_path} not found")
        return False
    
    try:
        # Test OCR extraction using our function
        with open(tax_file_path, 'rb') as file_obj:
            extracted_text = extract_text_from_file(file_obj)
        
        if extracted_text and extracted_text.strip():
            print(f"✅ OCR extraction successful!")
            print(f"📄 Extracted text length: {len(extracted_text)} characters")
            print(f"📄 First 200 characters: {extracted_text[:200]}...")
            print(f"📄 Full extracted text:")
            print("-" * 50)
            print(extracted_text)
            print("-" * 50)
            return True
        else:
            print("⚠️  OCR extraction returned empty text")
            return False
            
    except Exception as e:
        print(f"❌ OCR extraction failed: {e}")
        return False

def test_tax_file_upload():
    """Test the complete file upload process with tax.png"""
    print("\n🔍 Testing complete file upload process...")
    
    try:
        import requests
        import json
        
        base_url = "http://localhost:5007"
        
        # Test file upload
        with open("tax.png", 'rb') as file_obj:
            files = {'fileUpload': file_obj}
            data = {
                'message': 'Please analyze this tax document and extract key information',
                'session_id': 'test_tax_session',
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
                
    except Exception as e:
        print(f"❌ File upload test failed: {e}")
        return None

def main():
    """Run all tests"""
    print("🚀 Starting tax file OCR tests...")
    
    # Test OCR extraction
    if test_tax_file_ocr():
        print("✅ OCR extraction test passed!")
        
        # Test complete upload process
        thread_id = test_tax_file_upload()
        if thread_id:
            print(f"✅ Complete upload test passed with thread_id: {thread_id}")
        else:
            print("❌ Complete upload test failed")
    else:
        print("❌ OCR extraction test failed")

if __name__ == "__main__":
    main() 