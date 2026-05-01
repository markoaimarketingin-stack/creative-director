#!/usr/bin/env python3
"""Quick script to upload a sample image to Knowledge Base for testing."""

import requests
from pathlib import Path
from PIL import Image
import io

# Create a simple test image
def create_test_image():
    """Create a simple 200x200 colorful test image."""
    img = Image.new('RGB', (200, 200), color='blue')
    pixels = img.load()
    # Add some red pixels
    for i in range(50, 150):
        for j in range(50, 150):
            pixels[i, j] = (255, 100, 50)
    
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    return img_bytes

# Upload to KB
def upload_sample():
    api_url = "http://127.0.0.1:8000/knowledge-base/images"
    
    # Create test image
    img_data = create_test_image()
    
    # Upload
    files = {
        'file': ('test_sample_1.png', img_data, 'image/png')
    }
    data = {
        'title': 'Sample Product Image 1'
    }
    
    response = requests.post(api_url, files=files, data=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")

if __name__ == '__main__':
    upload_sample()
    print("✓ Sample image uploaded to Knowledge Base!")
