"""
Example 03 — Clipfly Image Combination
========================================
Blend 2 or more images into one AI-generated composition.

Run:
    python3 examples/03_image_combination.py
"""

import sys
sys.path.insert(0, "..")

from client import AIClient

API_URL = "http://localhost:3000/api"

client = AIClient(API_URL)

# Change these to your actual image file paths (minimum 2 required)
IMAGE_1 = "photo1.jpg"
IMAGE_2 = "photo2.jpg"

print("Combining images...")
result = client.clipfly_image_combination(
    prompt="Blend these images into a seamless cinematic scene with dramatic lighting",
    image_paths=[IMAGE_1, IMAGE_2],
    size="1:1"   # Options: "1:1", "16:9", "9:16", "3:4", "4:3"
)

print(f"\n✅ Combined image ready!")
print(f"   URL: {result['url']}")
