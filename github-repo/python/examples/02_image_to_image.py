"""
Example 02 — Clipfly Image to Image
=====================================
Transform an existing image using AI.

Run:
    python3 examples/02_image_to_image.py
"""

import sys
sys.path.insert(0, "..")

from client import AIClient

API_URL = "http://localhost:3000/api"

client = AIClient(API_URL)

# Change this to your actual image file path
IMAGE_PATH = "my_photo.jpg"

print("Transforming image...")
result = client.clipfly_image_to_image(
    prompt="Transform into anime art style with vibrant neon colors",
    image_path=IMAGE_PATH
)

print(f"\n✅ Transformed image ready!")
print(f"   URL: {result['url']}")
