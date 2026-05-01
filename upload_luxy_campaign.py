#!/usr/bin/env python3
"""Upload all images from LUXY campaign to Knowledge Base."""

import requests
from pathlib import Path
import sys

API_BASE = "http://127.0.0.1:8000"
OUTPUT_DIR = Path("output/luxy-conversions-meta")

def upload_images():
    """Find and upload all LUXY campaign images."""
    if not OUTPUT_DIR.exists():
        print(f"❌ Output directory not found: {OUTPUT_DIR}")
        return

    # Find all image files
    image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.webp'}
    image_files = []
    
    for img_path in OUTPUT_DIR.rglob('*'):
        if img_path.suffix.lower() in image_extensions:
            image_files.append(img_path)
    
    if not image_files:
        print(f"⚠️  No images found in {OUTPUT_DIR}")
        return

    print(f"📸 Found {len(image_files)} images in LUXY campaign")
    print("🚀 Uploading to Knowledge Base...")
    
    uploaded = 0
    failed = 0
    
    for idx, img_path in enumerate(image_files, 1):
        try:
            # Create title from path
            rel_path = img_path.relative_to(OUTPUT_DIR)
            parts = str(rel_path).split('\\')
            timestamp = parts[0] if parts else "unknown"
            folder = parts[1] if len(parts) > 1 else "image"
            filename = img_path.stem
            
            title = f"LUXY | {timestamp} | {folder} | {filename}"
            
            with open(img_path, 'rb') as f:
                files = {
                    'file': (img_path.name, f, 'image/png' if img_path.suffix.lower() == '.png' else 'image/jpeg')
                }
                data = {'title': title}
                
                resp = requests.post(f"{API_BASE}/knowledge-base/images", files=files, data=data)
                
                if resp.status_code == 200:
                    print(f"✓ [{idx}/{len(image_files)}] {title}")
                    uploaded += 1
                else:
                    print(f"✗ [{idx}/{len(image_files)}] {title} - Status {resp.status_code}")
                    failed += 1
        except Exception as e:
            print(f"✗ Error uploading {img_path.name}: {e}")
            failed += 1
    
    print(f"\n{'='*60}")
    print(f"📊 Upload Summary:")
    print(f"   ✓ Successfully uploaded: {uploaded}")
    print(f"   ✗ Failed: {failed}")
    print(f"   📦 Total: {len(image_files)}")
    print(f"{'='*60}")

if __name__ == '__main__':
    upload_images()
