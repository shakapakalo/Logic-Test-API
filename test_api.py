"""
AI API Test Script — Full Feature Test
Each call auto-creates a fresh account. No tokens needed upfront.

Usage:
    pip install requests pillow
    python3 test_api.py

Set BASE_URL to your deployed URL or keep localhost for local testing.
"""

import requests
import base64
import time
import io
import sys
import json
from PIL import Image

# ─────────────────────────────────────────────
BASE_URL = "https://19f63c47-d223-403a-acda-b00ea5f399fd-00-3dtu0n0m4dnud.picard.replit.dev/api"
POLL_INTERVAL = 5        # seconds between status polls
MAX_POLL = 60            # max poll attempts (~5 minutes)
SEP = "=" * 60
# ─────────────────────────────────────────────


def ok(label, data):
    body = json.dumps(data, indent=4)[:400]
    print(f"  [PASS] {label}")
    print(f"         {body}\n")


def fail(label, info):
    print(f"  [FAIL] {label}")
    print(f"         {info}\n")


def section(title):
    print(f"\n{SEP}\n  {title}\n{SEP}")


def make_b64(w=300, h=300, color=(100, 149, 237)):
    img = Image.new("RGB", (w, h), color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return base64.b64encode(buf.getvalue()).decode()


def poll_image(queue_id, token, label="Image"):
    print(f"  Polling {label} — queue_id={queue_id}")
    for i in range(MAX_POLL):
        r = requests.get(
            f"{BASE_URL}/clipfly/image-status",
            params={"queue_id": queue_id},
            headers={"Authorization": token},
            timeout=15,
        )
        d = r.json()
        s = d.get("status", "?")
        print(f"    [{i+1:02d}] {s}")
        if s == "completed":
            print(f"    URL: {d.get('url')}")
            return d
        if s == "failed":
            print(f"    Reason: {d.get('reason')}")
            return d
        time.sleep(POLL_INTERVAL)
    print("    Timed out.")
    return None


def poll_video_clipfly(queue_id, token, label="Video"):
    print(f"  Polling {label} — queue_id={queue_id}")
    for i in range(MAX_POLL):
        r = requests.get(
            f"{BASE_URL}/clipfly/video-status",
            params={"queue_id": queue_id},
            headers={"Authorization": token},
            timeout=15,
        )
        d = r.json()
        s = d.get("status", "?")
        print(f"    [{i+1:02d}] {s}")
        if s == "completed":
            print(f"    URL: {d.get('url')}")
            return d
        if s == "failed":
            print(f"    Reason: {d.get('reason')}")
            return d
        time.sleep(POLL_INTERVAL)
    print("    Timed out.")
    return None


def poll_geminigen(uuid, access_token, label="GeminiGen"):
    print(f"  Polling {label} — uuid={uuid[:20]}...")
    for i in range(MAX_POLL):
        r = requests.get(
            f"{BASE_URL}/geminigen/status/{uuid}",
            params={"access_token": access_token},
            timeout=15,
        )
        d = r.json()
        s = d.get("status", "?")
        print(f"    [{i+1:02d}] {s}")
        if s == "completed":
            print(f"    URL: {d.get('video_url')}")
            return d
        if s == "failed":
            print(f"    Reason: {d.get('reason')}")
            return d
        time.sleep(POLL_INTERVAL)
    print("    Timed out.")
    return None


# ─────────────────────────────────────────────
# TESTS
# ─────────────────────────────────────────────

results = {}


def run(name, fn):
    try:
        result = fn()
        results[name] = result is not None and result is not False
        return result
    except Exception as e:
        fail(name, str(e))
        results[name] = False
        return None


def test_health():
    section("1. Health Check")
    r = requests.get(f"{BASE_URL}/healthz", timeout=10)
    ok("GET /healthz", r.json())
    return r.json().get("status") == "ok"


def test_clipfly_t2i():
    section("2. Clipfly — Text to Image (fresh account auto-created)")
    r = requests.post(f"{BASE_URL}/clipfly/text-to-image", json={
        "prompt": "A stunning sunset over ocean with golden reflections",
        "size_id": "16:9"
    }, timeout=60)
    d = r.json()
    if not d.get("success"):
        fail("text-to-image", d)
        return None
    ok("POST /clipfly/text-to-image", {"queue_id": d["queue_id"], "token": d["token"][:40] + "..."})
    result = poll_image(d["queue_id"], d["token"], "Text-to-Image")
    return result


def test_clipfly_i2i():
    section("3. Clipfly — Image to Image (fresh account auto-created)")
    b64 = make_b64(400, 400, (255, 100, 50))
    r = requests.post(f"{BASE_URL}/clipfly/image-to-image", json={
        "prompt": "Transform into anime art style with vibrant colors",
        "base64": b64,
        "filename": "test.jpg"
    }, timeout=90)
    d = r.json()
    if not d.get("success"):
        fail("image-to-image", d)
        return None
    ok("POST /clipfly/image-to-image", {"queue_id": d["queue_id"]})
    result = poll_image(d["queue_id"], d["token"], "Image-to-Image")
    return result


def test_clipfly_combo():
    section("4. Clipfly — Image Combination (fresh account auto-created)")
    img1 = make_b64(300, 300, (60, 120, 200))
    img2 = make_b64(300, 300, (200, 100, 60))
    r = requests.post(f"{BASE_URL}/clipfly/image-combination", json={
        "prompt": "Blend these into one artistic composition",
        "images": [
            {"base64": img1, "filename": "img1.jpg"},
            {"base64": img2, "filename": "img2.jpg"}
        ],
        "size_id": "1:1"
    }, timeout=120)
    d = r.json()
    if not d.get("success"):
        fail("image-combination", d)
        return None
    ok("POST /clipfly/image-combination", {"queue_id": d["queue_id"]})
    result = poll_image(d["queue_id"], d["token"], "Image-Combination")
    return result


def test_clipfly_t2v():
    section("5. Clipfly — Text to Video (fresh account auto-created)")
    r = requests.post(f"{BASE_URL}/clipfly/text-to-video", json={
        "prompt": "Eagle soaring over mountains at golden hour, cinematic",
        "model": "wan",
        "ratio": "16:9"
    }, timeout=60)
    d = r.json()
    if not d.get("success"):
        fail("text-to-video", d)
        return None
    ok("POST /clipfly/text-to-video", {"queue_id": d["queue_id"]})
    result = poll_video_clipfly(d["queue_id"], d["token"], "Text-to-Video")
    return result


def test_clipfly_i2v():
    section("6. Clipfly — Image to Video (fresh account auto-created)")
    b64 = make_b64(640, 360, (50, 120, 200))
    r = requests.post(f"{BASE_URL}/clipfly/image-to-video", json={
        "prompt": "The scene comes alive with dramatic cinematic motion",
        "base64": b64,
        "filename": "scene.jpg",
        "model": "wan"
    }, timeout=90)
    d = r.json()
    if not d.get("success"):
        fail("image-to-video", d)
        return None
    ok("POST /clipfly/image-to-video", {"queue_id": d["queue_id"]})
    result = poll_video_clipfly(d["queue_id"], d["token"], "Image-to-Video")
    return result


def test_geminigen_veo_fast():
    section("7. GeminiGen — Veo Fast Text-to-Video (fresh account auto-created)")
    r = requests.post(f"{BASE_URL}/geminigen/video-gen", json={
        "prompt": "A futuristic city at night with neon lights reflecting on wet streets",
        "model": "veo_fast",
        "aspect_ratio": "16:9"
    }, timeout=60)
    d = r.json()
    if not d.get("success"):
        fail("geminigen veo_fast", d)
        return None
    ok("POST /geminigen/video-gen (veo_fast)", {"uuid": d["uuid"]})
    result = poll_geminigen(d["uuid"], d["access_token"], "Veo Fast")
    return result


def test_geminigen_veo_lite():
    section("8. GeminiGen — Veo Lite Text-to-Video (fresh account auto-created)")
    r = requests.post(f"{BASE_URL}/geminigen/video-gen", json={
        "prompt": "Gentle waves on a tropical beach at sunrise",
        "model": "veo_lite",
        "aspect_ratio": "9:16"
    }, timeout=60)
    d = r.json()
    if not d.get("success"):
        fail("geminigen veo_lite", d)
        return None
    ok("POST /geminigen/video-gen (veo_lite)", {"uuid": d["uuid"]})
    result = poll_geminigen(d["uuid"], d["access_token"], "Veo Lite")
    return result


def test_geminigen_veo_image():
    section("9. GeminiGen — Veo Fast Image-to-Video (fresh account auto-created)")
    b64 = make_b64(640, 360, (60, 120, 200))
    r = requests.post(f"{BASE_URL}/geminigen/video-gen", json={
        "prompt": "This scene bursts into life with dramatic slow motion",
        "model": "veo_fast",
        "aspect_ratio": "16:9",
        "images": [{"base64": b64, "filename": "scene.jpg"}]
    }, timeout=60)
    d = r.json()
    if not d.get("success"):
        fail("geminigen veo_fast + image", d)
        return None
    ok("POST /geminigen/video-gen (veo_fast + image)", {"uuid": d["uuid"]})
    result = poll_geminigen(d["uuid"], d["access_token"], "Veo+Image")
    return result


def test_geminigen_grok():
    section("10. GeminiGen — Grok Image-to-Video (fresh account auto-created)")
    b64 = make_b64(640, 480, (80, 200, 120))
    r = requests.post(f"{BASE_URL}/geminigen/video-gen", json={
        "prompt": "The image transforms with surreal floating elements and epic scale",
        "model": "grok",
        "aspect_ratio": "16:9",
        "images": [{"base64": b64, "filename": "input.jpg"}]
    }, timeout=60)
    d = r.json()
    if not d.get("success"):
        fail("geminigen grok", d)
        return None
    ok("POST /geminigen/video-gen (grok)", {"uuid": d["uuid"]})
    result = poll_geminigen(d["uuid"], d["access_token"], "Grok")
    return result


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print(f"\n{SEP}")
    print(f"  AI API Full Test")
    print(f"  URL: {BASE_URL}")
    print(SEP)

    run("1. Health",                test_health)
    run("2. Clipfly Text→Image",    test_clipfly_t2i)
    run("3. Clipfly Image→Image",   test_clipfly_i2i)
    run("4. Clipfly Image Combo",   test_clipfly_combo)
    run("5. Clipfly Text→Video",    test_clipfly_t2v)
    run("6. Clipfly Image→Video",   test_clipfly_i2v)
    run("7. GeminiGen Veo Fast",    test_geminigen_veo_fast)
    run("8. GeminiGen Veo Lite",    test_geminigen_veo_lite)
    run("9. GeminiGen Veo+Image",   test_geminigen_veo_image)
    run("10. GeminiGen Grok",       test_geminigen_grok)

    # ─── Summary ───
    print(f"\n{SEP}")
    print("  RESULTS")
    print(SEP)
    passed = sum(1 for v in results.values() if v)
    failed = sum(1 for v in results.values() if not v)
    for k, v in results.items():
        print(f"  {'PASS' if v else 'FAIL'}  {k}")
    print(f"\n  {passed} passed / {failed} failed / {len(results)} total")
    print(SEP + "\n")

    sys.exit(0 if failed == 0 else 1)
