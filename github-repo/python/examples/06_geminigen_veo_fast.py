"""
Example 06 — GeminiGen Veo Fast (Text to Video)
==================================================
Generate a high-quality video using Google Veo 3.1 Fast model.
A fresh anonymous account is auto-created every call.

Run:
    python3 examples/06_geminigen_veo_fast.py
"""

import sys
sys.path.insert(0, "..")

from client import AIClient

API_URL = "http://localhost:3000/api"

client = AIClient(API_URL, poll_interval=10)

print("Generating video with Veo Fast...")
result = client.geminigen_text_to_video(
    prompt="A futuristic city at night with neon lights reflecting on wet streets, cinematic drone shot",
    model="veo_fast",       # "veo_fast" or "veo_lite"
    aspect_ratio="16:9"     # "16:9", "9:16", "1:1"
)

print(f"\n✅ Video ready!")
print(f"   URL: {result['video_url']}")
