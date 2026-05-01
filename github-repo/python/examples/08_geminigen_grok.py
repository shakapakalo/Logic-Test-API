"""
Example 08 — GeminiGen Grok (Image to Video)
==============================================
Generate a video from 1–3 images using Grok Video model.
Grok supports up to 3 input images.

Run:
    python3 examples/08_geminigen_grok.py
"""

import sys
sys.path.insert(0, "..")

from client import AIClient

API_URL = "http://localhost:3000/api"

client = AIClient(API_URL, poll_interval=10)

# Change these to your actual image file paths (1 to 3 images)
IMAGES = [
    "photo1.jpg",
    # "photo2.jpg",  # optional second image
    # "photo3.jpg",  # optional third image
]

print("Generating video from image(s) with Grok...")
result = client.geminigen_image_to_video(
    prompt="The image transforms with surreal floating elements, epic scale, and dramatic lighting",
    image_paths=IMAGES,
    model="grok",
    aspect_ratio="16:9"   # "16:9", "9:16", "1:1"
)

print(f"\n✅ Video ready!")
print(f"   URL: {result['video_url']}")
