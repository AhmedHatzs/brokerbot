#!/usr/bin/env python3
"""
Test script for OCR functionality
"""

import os
import sys
from PIL import Image
import pytesseract

# Import the OCR function from chat_api
sys.path.append('.')
from chat_api import extract_text_from_file

def test_tesseract_installation():
    """Test if Tesseract is properly installed"""
    try:
        # Test basic Tesseract installation
        version = pytesseract.get_tesseract_version()
        print(f"✅ Tesseract version: {version}")
        return True
    except Exception as e:
        print(f"❌ Tesseract installation test failed: {e}")
        return False

def test_ocr_extraction():
    """Test OCR text extraction from a simple file"""
    try:
        # Create a simple test image with text (if PIL is working)
        from PIL import Image, ImageDraw, ImageFont
        
        # Create a white image
        img = Image.new('RGB', (400, 100), color='white')
        draw = ImageDraw.Draw(img)
        
        # Add text to the image
        try:
            # Try to use a default font
            font = ImageFont.load_default()
        except:
            # Fallback if font loading fails
            font = None
        
        draw.text((10, 10), "Test OCR Text", fill='black', font=font)
        
        # Save the test image
        test_image_path = "test_ocr_file.png"
        img.save(test_image_path)
        
        # Test OCR extraction using our function
        with open(test_image_path, 'rb') as file_obj:
            extracted_text = extract_text_from_file(file_obj, test_image_path)
        
        # Clean up
        if os.path.exists(test_image_path):
            os.remove(test_image_path)
        
        if extracted_text and extracted_text.strip():
            print(f"✅ OCR extraction test successful: '{extracted_text.strip()}'")
            return True
        else:
            print("⚠️  OCR extraction returned empty text")
            return False
            
    except Exception as e:
        print(f"❌ OCR extraction test failed: {e}")
        return False

def main():
    """Run all OCR tests"""
    print("🔍 Testing OCR functionality...")
    
    # Test Tesseract installation
    if not test_tesseract_installation():
        print("❌ Tesseract installation test failed")
        sys.exit(1)
    
    # Test OCR extraction
    if not test_ocr_extraction():
        print("❌ OCR extraction test failed")
        sys.exit(1)
    
    print("✅ All OCR tests passed!")

if __name__ == "__main__":
    main() 