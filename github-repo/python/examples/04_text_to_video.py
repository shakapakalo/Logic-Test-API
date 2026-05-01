"""
Example 04 — Clipfly Text to Video
=====================================
Generate a video from a text prompt.

Models:
  "wan"      — 10 second video (default)
  "seedance" — 5 second video (faster)

Run:
    python3 examples/04_text_to_video.py
"""

import sys
sys.path.insert(0, "..")

from client import AIClient

API_URL = "http://localhost:3000/api"

client = AIClient(API_URL)

print("Generating video from text...")
result = client.clipfly_text_to_video(
    prompt="An eagle soaring majestically over snow-capped mountains at golden hour, cinematic 4K",
    model="wan",       # "wan" or "seedance"
    ratio="16:9"       # "16:9", "9:16", "1:1"
)

print(f"\n✅ Video ready!")
print(f"   URL: {result['url']}")
