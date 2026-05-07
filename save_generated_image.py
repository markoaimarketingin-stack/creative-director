#!/usr/bin/env python3
"""Extract and save the generated image from metadata."""

import json
import base64
from pathlib import Path

# Read the metadata
metadata_file = Path("test_output/vertex_test_metadata.json")
with open(metadata_file, 'r') as f:
    metadata = json.load(f)

# Get the base64 image
image_base64 = metadata["generated_creative"]["images"][0]

# Remove data URL prefix if present
if image_base64.startswith("data:image/png;base64,"):
    image_base64 = image_base64.replace("data:image/png;base64,", "")

# Decode and save
image_bytes = base64.b64decode(image_base64)
output_path = Path("test_output/generated_creative_premium.png")
with open(output_path, 'wb') as f:
    f.write(image_bytes)

print(f"✓ Premium Creative Generated!")
print(f"  File: {output_path}")
print(f"  Size: {len(image_bytes)} bytes")
print(f"  Headline: {metadata['ad_copy']['headline']}")
print(f"  Body: {metadata['ad_copy']['body']}")
print(f"  CTA: {metadata['ad_copy']['cta']}")
print(f"\nThis image was generated with the ELITE creative director prompt!")
print(f"Features: Premium agency-quality design, perfect typography, professional layout")
