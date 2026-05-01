"""
Example 07 — GeminiGen Veo Fast (Image to Video)
==================================================
Animate an image into a video using Google Veo 3.1 Fast.
Pass up to 1 image for Veo models.

Run:
    python3 examples/07_geminigen_veo_with_image.py
"""

import sys
sys.path.insert(0, "..")

from client import AIClient

API_URL = "http://localhost:3000/api"

client = AIClient(API_URL, poll_interval=10)

# Change this to your actual image file path
IMAGE_PATH = "my_photo.jpg"

print("Generating video from image with Veo Fast...")
result = client.geminigen_image_to_video(
    prompt="The scene comes to life with dramatic camera movement and cinematic depth",
    image_paths=[IMAGE_PATH],   # Veo supports 1 image
    model="veo_fast",
    aspect_ratio="16:9"
)

print(f"\n✅ Video ready!")
print(f"   URL: {result['video_url']}")
