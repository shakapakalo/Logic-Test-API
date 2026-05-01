"""
Professional API Test Script
Tests all Clipfly and GeminiGen endpoints.

Usage:
    python3 test_api.py

Requirements:
    pip install requests pillow

Set BASE_URL to your deployed API or keep localhost for local testing.
"""

import requests
import base64
import time
import io
import sys
import json
from PIL import Image

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
BASE_URL = "http://localhost:80/api"   # Change to your deployed URL if needed
POLL_INTERVAL = 5        # seconds between status polls
MAX_POLL_ATTEMPTS = 60   # max polling attempts (~5 minutes)

SEPARATOR = "=" * 60

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def ok(label: str, data: dict):
    print(f"  [OK] {label}")
    print(f"       {json.dumps(data, indent=6)[:300]}")

def fail(label: str, resp: requests.Response):
    print(f"  [FAIL] {label} — HTTP {resp.status_code}")
    try:
        print(f"         {resp.json()}")
    except Exception:
        print(f"         {resp.text[:200]}")

def section(title: str):
    print(f"\n{SEPARATOR}")
    print(f"  {title}")
    print(SEPARATOR)

def make_test_image_b64(width=100, height=100, color=(100, 149, 237)) -> str:
    """Create a small JPEG image and return as base64 string."""
    img = Image.new("RGB", (width, height), color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return base64.b64encode(buf.getvalue()).decode()

def poll_image_status(queue_id: str, token: str, label="Image Task") -> dict | None:
    """Poll Clipfly image status until completed/failed/timeout."""
    print(f"  Polling {label} (queue_id={queue_id[:20]}...)")
    for attempt in range(MAX_POLL_ATTEMPTS):
        resp = requests.get(
            f"{BASE_URL}/clipfly/image-status",
            params={"queue_id": queue_id, "token": token},
            timeout=15,
        )
        if resp.status_code == 200:
            data = resp.json()
            status = data.get("status", "unknown")
            print(f"  [{attempt+1:02d}] status={status}")
            if status == "completed":
                return data
            elif status == "failed":
                print(f"  Task failed: {data.get('reason')}")
                return data
        time.sleep(POLL_INTERVAL)
    print("  Polling timed out.")
    return None

def poll_video_status_clipfly(queue_id: str, token: str, label="Video Task") -> dict | None:
    """Poll Clipfly video status until completed/failed/timeout."""
    print(f"  Polling {label} (queue_id={queue_id[:20]}...)")
    for attempt in range(MAX_POLL_ATTEMPTS):
        resp = requests.get(
            f"{BASE_URL}/clipfly/video-status",
            params={"queue_id": queue_id, "token": token},
            timeout=15,
        )
        if resp.status_code == 200:
            data = resp.json()
            status = data.get("status", "unknown")
            print(f"  [{attempt+1:02d}] status={status} raw={data.get('raw_status')}")
            if status == "completed":
                return data
            elif status == "failed":
                print(f"  Task failed: {data.get('reason')}")
                return data
        time.sleep(POLL_INTERVAL)
    print("  Polling timed out.")
    return None

def poll_geminigen_status(uuid: str, access_token: str) -> dict | None:
    """Poll GeminiGen video status until completed/failed/timeout."""
    print(f"  Polling GeminiGen task (uuid={uuid[:20]}...)")
    for attempt in range(MAX_POLL_ATTEMPTS):
        resp = requests.get(
            f"{BASE_URL}/geminigen/status/{uuid}",
            params={"access_token": access_token},
            timeout=15,
        )
        if resp.status_code == 200:
            data = resp.json()
            status = data.get("status", "unknown")
            print(f"  [{attempt+1:02d}] status={status}")
            if status == "completed":
                return data
            elif status == "failed":
                print(f"  Task failed: {data.get('reason')}")
                return data
        time.sleep(POLL_INTERVAL)
    print("  Polling timed out.")
    return None


# ─────────────────────────────────────────────
# TEST SUITES
# ─────────────────────────────────────────────

def test_health():
    section("1. Health Check")
    resp = requests.get(f"{BASE_URL}/healthz", timeout=10)
    if resp.status_code == 200:
        ok("GET /api/healthz", resp.json())
    else:
        fail("GET /api/healthz", resp)
    return resp.status_code == 200


def test_clipfly_register() -> str | None:
    section("2. Clipfly — Register Account")
    resp = requests.post(f"{BASE_URL}/clipfly/register", timeout=60)
    if resp.status_code == 200 and resp.json().get("success"):
        data = resp.json()
        ok("POST /api/clipfly/register", {"email": data["email"], "token": data["token"][:30] + "..."})
        return data["token"]
    else:
        fail("POST /api/clipfly/register", resp)
        return None


def test_clipfly_upload(token: str) -> tuple[str | None, str | None]:
    section("3. Clipfly — Upload Image")
    b64 = make_test_image_b64(200, 200, (255, 120, 60))
    resp = requests.post(
        f"{BASE_URL}/clipfly/upload",
        json={"token": token, "base64": b64, "filename": "test_upload.jpg"},
        timeout=60,
    )
    if resp.status_code == 200 and resp.json().get("success"):
        data = resp.json()
        ok("POST /api/clipfly/upload", data)
        return data["storage_path"], data.get("user_id")
    else:
        fail("POST /api/clipfly/upload", resp)
        return None, None


def test_clipfly_text_to_image(token: str) -> str | None:
    section("4. Clipfly — Text to Image")
    resp = requests.post(
        f"{BASE_URL}/clipfly/text-to-image",
        json={
            "token": token,
            "prompt": "A stunning sunset over a calm ocean with golden reflections",
            "size_id": "16:9",
        },
        timeout=60,
    )
    if resp.status_code == 200 and resp.json().get("success"):
        queue_id = resp.json()["queue_id"]
        ok("POST /api/clipfly/text-to-image", {"queue_id": queue_id})

        # Poll for result
        result = poll_image_status(queue_id, token, "Text-to-Image")
        if result and result.get("status") == "completed":
            print(f"  Result URL: {result.get('url')}")
        return queue_id
    else:
        fail("POST /api/clipfly/text-to-image", resp)
        return None


def test_clipfly_image_to_image(token: str, storage_path: str, material_id: str) -> str | None:
    section("5. Clipfly — Image to Image")
    resp = requests.post(
        f"{BASE_URL}/clipfly/image-to-image",
        json={
            "token": token,
            "prompt": "Transform into an anime art style with vibrant colors",
            "source_image": storage_path,
            "material_id": material_id,
        },
        timeout=60,
    )
    if resp.status_code == 200 and resp.json().get("success"):
        queue_id = resp.json()["queue_id"]
        ok("POST /api/clipfly/image-to-image", {"queue_id": queue_id})

        result = poll_image_status(queue_id, token, "Image-to-Image")
        if result and result.get("status") == "completed":
            print(f"  Result URL: {result.get('url')}")
        return queue_id
    else:
        fail("POST /api/clipfly/image-to-image", resp)
        return None


def test_clipfly_image_combination(token: str, paths: list, material_ids: list) -> str | None:
    section("6. Clipfly — Image Combination")
    if len(paths) < 2:
        print("  Skipped: need at least 2 uploaded images for combination.")
        return None

    resp = requests.post(
        f"{BASE_URL}/clipfly/image-combination",
        json={
            "token": token,
            "prompt": "Blend these images into a cohesive artistic composition",
            "source_images": paths,
            "material_ids": material_ids,
            "size_id": "1:1",
        },
        timeout=60,
    )
    if resp.status_code == 200 and resp.json().get("success"):
        queue_id = resp.json()["queue_id"]
        ok("POST /api/clipfly/image-combination", {"queue_id": queue_id})

        result = poll_image_status(queue_id, token, "Image-Combination")
        if result and result.get("status") == "completed":
            print(f"  Result URL: {result.get('url')}")
        return queue_id
    else:
        fail("POST /api/clipfly/image-combination", resp)
        return None


def test_clipfly_text_to_video(token: str) -> str | None:
    section("7. Clipfly — Text to Video")
    resp = requests.post(
        f"{BASE_URL}/clipfly/text-to-video",
        json={
            "token": token,
            "prompt": "A majestic eagle soaring through mountain clouds at golden hour",
            "model": "wan",
            "ratio": "16:9",
        },
        timeout=60,
    )
    if resp.status_code == 200 and resp.json().get("success"):
        queue_id = resp.json()["queue_id"]
        ok("POST /api/clipfly/text-to-video", {"queue_id": queue_id})

        result = poll_video_status_clipfly(queue_id, token, "Text-to-Video")
        if result and result.get("status") == "completed":
            print(f"  Video URL: {result.get('url')}")
        return queue_id
    else:
        fail("POST /api/clipfly/text-to-video", resp)
        return None


def test_clipfly_image_to_video(token: str, storage_path: str) -> str | None:
    section("8. Clipfly — Image to Video")
    resp = requests.post(
        f"{BASE_URL}/clipfly/image-to-video",
        json={
            "token": token,
            "prompt": "Bring this image to life with gentle motion and cinematic depth",
            "source_image": storage_path,
            "model": "wan",
        },
        timeout=60,
    )
    if resp.status_code == 200 and resp.json().get("success"):
        queue_id = resp.json()["queue_id"]
        ok("POST /api/clipfly/image-to-video", {"queue_id": queue_id})

        result = poll_video_status_clipfly(queue_id, token, "Image-to-Video")
        if result and result.get("status") == "completed":
            print(f"  Video URL: {result.get('url')}")
        return queue_id
    else:
        fail("POST /api/clipfly/image-to-video", resp)
        return None


def test_geminigen_token() -> str | None:
    section("9. GeminiGen — Get Access Token")
    resp = requests.post(f"{BASE_URL}/geminigen/token", timeout=60)
    if resp.status_code == 200 and resp.json().get("success"):
        token = resp.json()["access_token"]
        ok("POST /api/geminigen/token", {"access_token": token[:40] + "..."})
        return token
    else:
        fail("POST /api/geminigen/token", resp)
        return None


def test_geminigen_veo_fast(access_token: str) -> str | None:
    section("10. GeminiGen — Veo Fast (text-to-video)")
    resp = requests.post(
        f"{BASE_URL}/geminigen/video-gen",
        json={
            "access_token": access_token,
            "prompt": "A futuristic city at night with neon lights reflecting on wet streets",
            "model": "veo_fast",
            "aspect_ratio": "16:9",
        },
        timeout=60,
    )
    if resp.status_code == 200 and resp.json().get("success"):
        uuid = resp.json()["uuid"]
        ok("POST /api/geminigen/video-gen (veo_fast)", {"uuid": uuid})

        result = poll_geminigen_status(uuid, access_token)
        if result and result.get("status") == "completed":
            print(f"  Video URL: {result.get('video_url')}")
        return uuid
    else:
        fail("POST /api/geminigen/video-gen (veo_fast)", resp)
        return None


def test_geminigen_veo_lite(access_token: str) -> str | None:
    section("11. GeminiGen — Veo Lite (text-to-video)")
    resp = requests.post(
        f"{BASE_URL}/geminigen/video-gen",
        json={
            "access_token": access_token,
            "prompt": "Gentle waves on a tropical beach at sunrise",
            "model": "veo_lite",
            "aspect_ratio": "9:16",
        },
        timeout=60,
    )
    if resp.status_code == 200 and resp.json().get("success"):
        uuid = resp.json()["uuid"]
        ok("POST /api/geminigen/video-gen (veo_lite)", {"uuid": uuid})

        result = poll_geminigen_status(uuid, access_token)
        if result and result.get("status") == "completed":
            print(f"  Video URL: {result.get('video_url')}")
        return uuid
    else:
        fail("POST /api/geminigen/video-gen (veo_lite)", resp)
        return None


def test_geminigen_veo_with_image(access_token: str) -> str | None:
    section("12. GeminiGen — Veo Fast (image-to-video)")
    b64 = make_test_image_b64(640, 360, (60, 120, 200))
    resp = requests.post(
        f"{BASE_URL}/geminigen/video-gen",
        json={
            "access_token": access_token,
            "prompt": "This scene comes alive with dramatic lighting and slow camera movement",
            "model": "veo_fast",
            "aspect_ratio": "16:9",
            "images": [{"base64": b64, "filename": "scene.jpg"}],
        },
        timeout=60,
    )
    if resp.status_code == 200 and resp.json().get("success"):
        uuid = resp.json()["uuid"]
        ok("POST /api/geminigen/video-gen (veo_fast + image)", {"uuid": uuid})

        result = poll_geminigen_status(uuid, access_token)
        if result and result.get("status") == "completed":
            print(f"  Video URL: {result.get('video_url')}")
        return uuid
    else:
        fail("POST /api/geminigen/video-gen (veo_fast + image)", resp)
        return None


def test_geminigen_grok(access_token: str) -> str | None:
    section("13. GeminiGen — Grok (image-to-video)")
    b64 = make_test_image_b64(640, 480, (80, 200, 120))
    resp = requests.post(
        f"{BASE_URL}/geminigen/video-gen",
        json={
            "access_token": access_token,
            "prompt": "The image transforms with surreal floating elements and epic scale",
            "model": "grok",
            "aspect_ratio": "16:9",
            "images": [{"base64": b64, "filename": "input.jpg"}],
        },
        timeout=60,
    )
    if resp.status_code == 200 and resp.json().get("success"):
        uuid = resp.json()["uuid"]
        ok("POST /api/geminigen/video-gen (grok)", {"uuid": uuid})

        result = poll_geminigen_status(uuid, access_token)
        if result and result.get("status") == "completed":
            print(f"  Video URL: {result.get('video_url')}")
        return uuid
    else:
        fail("POST /api/geminigen/video-gen (grok)", resp)
        return None


def test_geminigen_status_check(access_token: str, uuid: str):
    section("14. GeminiGen — Manual Status Check")
    resp = requests.get(
        f"{BASE_URL}/geminigen/status/{uuid}",
        params={"access_token": access_token},
        timeout=15,
    )
    if resp.status_code == 200:
        ok(f"GET /api/geminigen/status/{uuid[:16]}...", resp.json())
    else:
        fail(f"GET /api/geminigen/status/{uuid[:16]}...", resp)


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    print("\n" + SEPARATOR)
    print("  AI API Test Suite")
    print(f"  Target: {BASE_URL}")
    print(SEPARATOR)

    results = {}

    # 1. Health
    results["health"] = test_health()
    if not results["health"]:
        print("\n  Server is not responding. Exiting.")
        sys.exit(1)

    # ──────── CLIPFLY TESTS ────────
    token = test_clipfly_register()
    results["clipfly_register"] = token is not None

    if token:
        storage_path, material_id = test_clipfly_upload(token)
        results["clipfly_upload"] = storage_path is not None

        # Upload a second image for combination test
        storage_path2, material_id2 = None, None
        if storage_path:
            b64_2 = make_test_image_b64(200, 200, (60, 180, 255))
            r2 = requests.post(
                f"{BASE_URL}/clipfly/upload",
                json={"token": token, "base64": b64_2, "filename": "test2.jpg"},
                timeout=60,
            )
            if r2.status_code == 200 and r2.json().get("success"):
                storage_path2 = r2.json()["storage_path"]
                material_id2 = r2.json().get("user_id")

        results["clipfly_t2i"] = test_clipfly_text_to_image(token) is not None

        if storage_path and material_id:
            results["clipfly_i2i"] = test_clipfly_image_to_image(token, storage_path, material_id) is not None

        if storage_path and storage_path2 and material_id and material_id2:
            results["clipfly_combo"] = test_clipfly_image_combination(
                token,
                [storage_path, storage_path2],
                [material_id, material_id2],
            ) is not None

        results["clipfly_t2v"] = test_clipfly_text_to_video(token) is not None

        if storage_path:
            results["clipfly_i2v"] = test_clipfly_image_to_video(token, storage_path) is not None

    # ──────── GEMINIGEN TESTS ────────
    g_token = test_geminigen_token()
    results["geminigen_token"] = g_token is not None

    if g_token:
        uuid_veo = test_geminigen_veo_fast(g_token)
        results["geminigen_veo_fast"] = uuid_veo is not None

        results["geminigen_veo_lite"] = test_geminigen_veo_lite(g_token) is not None
        results["geminigen_veo_image"] = test_geminigen_veo_with_image(g_token) is not None
        results["geminigen_grok"] = test_geminigen_grok(g_token) is not None

        if uuid_veo:
            test_geminigen_status_check(g_token, uuid_veo)

    # ──────── SUMMARY ────────
    print(f"\n{SEPARATOR}")
    print("  RESULTS SUMMARY")
    print(SEPARATOR)
    passed = 0
    failed = 0
    for key, val in results.items():
        icon = "PASS" if val else "FAIL"
        print(f"  [{icon}] {key}")
        if val:
            passed += 1
        else:
            failed += 1
    print(f"\n  Total: {passed} passed, {failed} failed out of {len(results)} tests")
    print(SEPARATOR + "\n")

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
