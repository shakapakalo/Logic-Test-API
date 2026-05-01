"""
Example 01 — Clipfly Text to Image
===================================
Generate an AI image from a text prompt.
A fresh account is auto-created each time — no signup needed.

Run:
    python3 examples/01_text_to_image.py
"""

import sys
sys.path.insert(0, "..")

from client import AIClient

API_URL = "http://localhost:3000/api"  # Change to your VPS IP

client = AIClient(API_URL)

if not client.health():
    print("ERROR: API server is not running. Start it first.")
    sys.exit(1)

print("Generating image from text...")
result = client.clipfly_text_to_image(
    prompt="A stunning sunset over the ocean with golden reflections on the water",
    size="16:9"
)

print(f"\n✅ Image ready!")
print(f"   URL: {result['url']}")
