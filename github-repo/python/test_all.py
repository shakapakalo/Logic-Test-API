"""
Full API Test — Tests all 10 endpoints automatically.
No accounts needed — all created automatically.

Usage:
    pip install -r requirements.txt
    python3 test_all.py [API_URL]

Example:
    python3 test_all.py http://YOUR_VPS_IP:3000/api
"""

import sys
import io
import base64
import time
import requests
from PIL import Image

API_URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:3000/api"
SEP = "=" * 60
RESULTS = {}


def section(title):
    print(f"\n{SEP}\n  {title}\n{SEP}")


def make_b64(color=(100, 149, 237)):
    img = Image.new("RGB", (400, 400), color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return base64.b64encode(buf.getvalue()).decode()


def poll_image(queue_id, token):
    for i in range(72):
        r = requests.get(f"{API_URL}/clipfly/image-status", params={"queue_id": queue_id}, headers={"Authorization": token}, timeout=15)
        d = r.json(); s = d.get("status")
        print(f"  [{i+1:02d}] {s}")
        if s == "completed": return d
        if s == "failed": raise RuntimeError(d.get("reason"))
        time.sleep(5)
    raise TimeoutError("Image timed out")


def poll_video(queue_id, token):
    for i in range(72):
        r = requests.get(f"{API_URL}/clipfly/video-status", params={"queue_id": queue_id}, headers={"Authorization": token}, timeout=15)
        d = r.json(); s = d.get("status")
        print(f"  [{i+1:02d}] {s}")
        if s == "completed": return d
        if s == "failed": raise RuntimeError(d.get("reason"))
        time.sleep(5)
    raise TimeoutError("Video timed out")


def poll_geminigen(uuid, access_token):
    for i in range(72):
        r = requests.get(f"{API_URL}/geminigen/status/{uuid}", params={"access_token": access_token}, timeout=15)
        d = r.json(); s = d.get("status")
        print(f"  [{i+1:02d}] {s}")
        if s == "completed": return d
        if s == "failed": raise RuntimeError(d.get("reason"))
        time.sleep(10)
    raise TimeoutError("GeminiGen timed out")


def test(name, fn):
    try:
        result = fn()
        RESULTS[name] = True
        return result
    except Exception as e:
        print(f"  ERROR: {e}")
        RESULTS[name] = False
        return None


# ─── Tests ────────────────────────────────────────────────────────────────────

print(f"\n{SEP}")
print(f"  AI API — Full Test Suite")
print(f"  URL: {API_URL}")
print(SEP)

section("1. Health Check")
def t_health():
    r = requests.get(f"{API_URL}/healthz", timeout=10)
    d = r.json()
    print(f"  {d}")
    assert d.get("status") == "ok"
    return d
test("1. Health", t_health)

section("2. Clipfly — Text to Image")
def t_t2i():
    r = requests.post(f"{API_URL}/clipfly/text-to-image", json={"prompt": "A sunset over the ocean", "size_id": "16:9"}, timeout=60)
    d = r.json()
    assert d.get("success"), d
    print(f"  Submitted. queue_id={d['queue_id']}")
    result = poll_image(d["queue_id"], d["token"])
    print(f"  URL: {result['url']}")
    return result
test("2. Clipfly Text→Image", t_t2i)

section("3. Clipfly — Image to Image")
def t_i2i():
    b64 = make_b64((255, 100, 50))
    r = requests.post(f"{API_URL}/clipfly/image-to-image", json={"prompt": "Anime art style", "base64": b64, "filename": "test.jpg"}, timeout=90)
    d = r.json()
    assert d.get("success"), d
    print(f"  Submitted. queue_id={d['queue_id']}")
    result = poll_image(d["queue_id"], d["token"])
    print(f"  URL: {result['url']}")
    return result
test("3. Clipfly Image→Image", t_i2i)

section("4. Clipfly — Image Combination")
def t_combo():
    b64a = make_b64((60, 120, 200)); b64b = make_b64((200, 100, 60))
    r = requests.post(f"{API_URL}/clipfly/image-combination", json={
        "prompt": "Blend into cinematic scene",
        "images": [{"base64": b64a, "filename": "a.jpg"}, {"base64": b64b, "filename": "b.jpg"}],
        "size_id": "1:1"
    }, timeout=120)
    d = r.json()
    assert d.get("success"), d
    print(f"  Submitted. queue_id={d['queue_id']}")
    result = poll_image(d["queue_id"], d["token"])
    print(f"  URL: {result['url']}")
    return result
test("4. Clipfly Image Combo", t_combo)

section("5. Clipfly — Text to Video")
def t_t2v():
    r = requests.post(f"{API_URL}/clipfly/text-to-video", json={"prompt": "Eagle soaring over mountains", "model": "wan", "ratio": "16:9"}, timeout=60)
    d = r.json()
    assert d.get("success"), d
    print(f"  Submitted. queue_id={d['queue_id']}")
    result = poll_video(d["queue_id"], d["token"])
    print(f"  URL: {result['url']}")
    return result
test("5. Clipfly Text→Video", t_t2v)

section("6. Clipfly — Image to Video")
def t_i2v():
    b64 = make_b64((50, 120, 200))
    r = requests.post(f"{API_URL}/clipfly/image-to-video", json={"prompt": "Cinematic motion", "base64": b64, "filename": "scene.jpg", "model": "wan"}, timeout=90)
    d = r.json()
    assert d.get("success"), d
    print(f"  Submitted. queue_id={d['queue_id']}")
    result = poll_video(d["queue_id"], d["token"])
    print(f"  URL: {result['url']}")
    return result
test("6. Clipfly Image→Video", t_i2v)

section("7. GeminiGen — Veo Fast (Text to Video)")
def t_veo_fast():
    r = requests.post(f"{API_URL}/geminigen/video-gen", json={"prompt": "Neon city at night", "model": "veo_fast", "aspect_ratio": "16:9"}, timeout=60)
    d = r.json()
    assert d.get("success"), d
    print(f"  Submitted. uuid={d['uuid']}")
    result = poll_geminigen(d["uuid"], d["access_token"])
    print(f"  URL: {result['video_url']}")
    return result
test("7. GeminiGen Veo Fast", t_veo_fast)

section("8. GeminiGen — Veo Lite (Text to Video)")
def t_veo_lite():
    r = requests.post(f"{API_URL}/geminigen/video-gen", json={"prompt": "Beach at sunrise", "model": "veo_lite", "aspect_ratio": "9:16"}, timeout=60)
    d = r.json()
    assert d.get("success"), d
    print(f"  Submitted. uuid={d['uuid']}")
    result = poll_geminigen(d["uuid"], d["access_token"])
    print(f"  URL: {result['video_url']}")
    return result
test("8. GeminiGen Veo Lite", t_veo_lite)

section("9. GeminiGen — Veo Fast + Image")
def t_veo_img():
    b64 = make_b64((60, 120, 200))
    r = requests.post(f"{API_URL}/geminigen/video-gen", json={
        "prompt": "The scene bursts into dramatic motion",
        "model": "veo_fast", "aspect_ratio": "16:9",
        "images": [{"base64": b64, "filename": "scene.jpg"}]
    }, timeout=60)
    d = r.json()
    assert d.get("success"), d
    print(f"  Submitted. uuid={d['uuid']}")
    result = poll_geminigen(d["uuid"], d["access_token"])
    print(f"  URL: {result['video_url']}")
    return result
test("9. GeminiGen Veo+Image", t_veo_img)

section("10. GeminiGen — Grok (Image to Video)")
def t_grok():
    b64 = make_b64((80, 200, 120))
    r = requests.post(f"{API_URL}/geminigen/video-gen", json={
        "prompt": "Surreal transformation with epic scale",
        "model": "grok", "aspect_ratio": "16:9",
        "images": [{"base64": b64, "filename": "input.jpg"}]
    }, timeout=60)
    d = r.json()
    assert d.get("success"), d
    print(f"  Submitted. uuid={d['uuid']}")
    result = poll_geminigen(d["uuid"], d["access_token"])
    print(f"  URL: {result['video_url']}")
    return result
test("10. GeminiGen Grok", t_grok)

# ─── Summary ──────────────────────────────────────────────────────────────────
print(f"\n{SEP}")
print("  RESULTS SUMMARY")
print(SEP)
passed = sum(1 for v in RESULTS.values() if v)
failed = sum(1 for v in RESULTS.values() if not v)
for k, v in RESULTS.items():
    print(f"  {'PASS' if v else 'FAIL'}  {k}")
print(f"\n  {passed} passed / {failed} failed / {len(RESULTS)} total")
print(SEP)
sys.exit(0 if failed == 0 else 1)
