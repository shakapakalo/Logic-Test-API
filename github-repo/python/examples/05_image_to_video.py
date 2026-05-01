"""
Example 05 — Clipfly Image to Video
======================================
Animate an existing image into a video.

Models:
  "wan"      — default model (10s)
  "seedance" — high quality (10s)
  "lumen"    — alternative style (10s)

Run:
    python3 examples/05_image_to_video.py
"""

import sys
sys.path.insert(0, "..")

from client import AIClient

API_URL = "http://localhost:3000/api"

client = AIClient(API_URL)

# Change this to your actual image file path
IMAGE_PATH = "my_photo.jpg"

print("Animating image into video...")
result = client.clipfly_image_to_video(
    prompt="The scene comes alive with gentle camera movement and dramatic lighting",
    image_path=IMAGE_PATH,
    model="wan"   # "wan", "seedance", or "lumen"
)

print(f"\n✅ Video ready!")
print(f"   URL: {result['url']}")
