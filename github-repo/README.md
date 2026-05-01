# AI API Server

A professional REST API server that wraps **Clipfly** (AI image & video generation) and **GeminiGen** (Veo & Grok video generation).

**Key feature:** Every request auto-creates a fresh account — no API keys, no sign-ups, no tokens needed from you.

---

## Features

| Service    | Feature             | Endpoint |
|------------|---------------------|----------|
| Clipfly    | Text → Image        | `POST /api/clipfly/text-to-image` |
| Clipfly    | Image → Image       | `POST /api/clipfly/image-to-image` |
| Clipfly    | Image Combination   | `POST /api/clipfly/image-combination` |
| Clipfly    | Text → Video        | `POST /api/clipfly/text-to-video` |
| Clipfly    | Image → Video       | `POST /api/clipfly/image-to-video` |
| GeminiGen  | Veo Fast (T2V/I2V)  | `POST /api/geminigen/video-gen` |
| GeminiGen  | Veo Lite (T2V/I2V)  | `POST /api/geminigen/video-gen` |
| GeminiGen  | Grok (I2V, 1-3 imgs)| `POST /api/geminigen/video-gen` |

---

## Quick Start — Contabo VPS

```bash
# 1. Clone this repo on your VPS
git clone https://github.com/YOUR_USER/YOUR_REPO.git
cd YOUR_REPO

# 2. Run one-command installer (requires root)
chmod +x install.sh
sudo ./install.sh
```

Done. Your API is live at `http://YOUR_VPS_IP/api`

See [docs/INSTALL.md](docs/INSTALL.md) for Docker and manual setup options.

---

## Quick Start — Docker

```bash
git clone https://github.com/YOUR_USER/YOUR_REPO.git
cd YOUR_REPO
docker compose up -d
```

API available at `http://localhost:3000/api`

---

## Python Usage

### Install

```bash
cd python
pip install -r requirements.txt
```

### Use the Client Library

```python
from client import AIClient

client = AIClient("http://YOUR_VPS_IP/api")

# Check server health
print(client.health())  # True

# Generate image from text
result = client.clipfly_text_to_image(
    prompt="A stunning sunset over the ocean",
    size="16:9"
)
print(result["url"])

# Transform an image
result = client.clipfly_image_to_image(
    prompt="Anime art style with vibrant colors",
    image_path="photo.jpg"
)
print(result["url"])

# Combine 2 images
result = client.clipfly_image_combination(
    prompt="Blend into one cinematic scene",
    image_paths=["photo1.jpg", "photo2.jpg"]
)
print(result["url"])

# Text to video
result = client.clipfly_text_to_video(
    prompt="Eagle soaring over snowy mountains",
    model="wan",    # "wan" or "seedance"
    ratio="16:9"
)
print(result["url"])

# Image to video
result = client.clipfly_image_to_video(
    prompt="Cinematic camera movement",
    image_path="scene.jpg",
    model="wan"    # "wan", "seedance", or "lumen"
)
print(result["url"])

# GeminiGen — text to video (Veo)
result = client.geminigen_text_to_video(
    prompt="Futuristic city at night with neon lights",
    model="veo_fast",     # "veo_fast", "veo_lite", or "grok"
    aspect_ratio="16:9"
)
print(result["video_url"])

# GeminiGen — image to video (Veo)
result = client.geminigen_image_to_video(
    prompt="The scene bursts into dramatic motion",
    image_paths=["scene.jpg"],  # 1 image for Veo, up to 3 for Grok
    model="veo_fast"
)
print(result["video_url"])
```

### Run All Examples

```bash
cd python

# Single features
python3 examples/01_text_to_image.py
python3 examples/02_image_to_image.py
python3 examples/03_image_combination.py
python3 examples/04_text_to_video.py
python3 examples/05_image_to_video.py
python3 examples/06_geminigen_veo_fast.py
python3 examples/07_geminigen_veo_with_image.py
python3 examples/08_geminigen_grok.py

# Full test suite (all 10 endpoints)
python3 test_all.py http://YOUR_VPS_IP/api
```

---

## API Quick Reference

### Clipfly — No tokens needed

```python
import requests

BASE = "http://YOUR_VPS_IP/api"

# Text to Image
r = requests.post(f"{BASE}/clipfly/text-to-image", json={
    "prompt": "A sunset over the ocean",
    "size_id": "16:9"    # 1:1 | 9:16 | 16:9 | 3:4 | 4:3 | 2:3 | 3:2 | 21:9
})
d = r.json()
queue_id = d["queue_id"]
token    = d["token"]    # Keep this — needed for polling

# Poll image status
import time
while True:
    s = requests.get(f"{BASE}/clipfly/image-status",
        params={"queue_id": queue_id},
        headers={"Authorization": token}).json()
    if s["status"] == "completed":
        print("Image URL:", s["url"])
        break
    elif s["status"] == "failed":
        print("Failed:", s.get("reason"))
        break
    time.sleep(5)
```

```python
import base64

# Image to Image
b64 = base64.b64encode(open("photo.jpg","rb").read()).decode()
r = requests.post(f"{BASE}/clipfly/image-to-image", json={
    "prompt": "Transform to oil painting style",
    "base64": b64,
    "filename": "photo.jpg"
})
# → poll with d["queue_id"] and d["token"] using /clipfly/image-status

# Image Combination (min 2 images)
r = requests.post(f"{BASE}/clipfly/image-combination", json={
    "prompt": "Blend into one scene",
    "images": [
        {"base64": b64_1, "filename": "img1.jpg"},
        {"base64": b64_2, "filename": "img2.jpg"}
    ],
    "size_id": "1:1"
})
# → poll with /clipfly/image-status

# Text to Video
r = requests.post(f"{BASE}/clipfly/text-to-video", json={
    "prompt": "Whale jumping out of the ocean at sunset",
    "model": "wan",      # "wan" (10s) or "seedance" (5s)
    "ratio": "16:9"
})
# → poll with d["queue_id"] and d["token"] using /clipfly/video-status

# Image to Video
r = requests.post(f"{BASE}/clipfly/image-to-video", json={
    "prompt": "The scene comes to life with slow camera pan",
    "base64": b64,
    "filename": "scene.jpg",
    "model": "wan"       # "wan", "seedance", or "lumen"
})
# → poll with /clipfly/video-status
```

### GeminiGen — No tokens needed

```python
# Text to Video (Veo Fast / Veo Lite)
r = requests.post(f"{BASE}/geminigen/video-gen", json={
    "prompt": "Mountain lake at dawn with mist",
    "model": "veo_fast",      # "veo_fast", "veo_lite", or "grok"
    "aspect_ratio": "16:9"    # "16:9", "9:16", "1:1"
})
d = r.json()
uuid         = d["uuid"]
access_token = d["access_token"]

# Image to Video (pass images array)
b64 = base64.b64encode(open("photo.jpg","rb").read()).decode()
r = requests.post(f"{BASE}/geminigen/video-gen", json={
    "prompt": "Epic cinematic motion",
    "model": "veo_fast",
    "aspect_ratio": "16:9",
    "images": [{"base64": b64, "filename": "photo.jpg"}]
    # For grok: up to 3 images
})

# Poll status
while True:
    s = requests.get(f"{BASE}/geminigen/status/{uuid}",
        params={"access_token": access_token}).json()
    if s["status"] == "completed":
        print("Video URL:", s["video_url"])
        break
    elif s["status"] == "failed":
        print("Failed:", s.get("reason"))
        break
    time.sleep(10)
```

---

## Project Structure

```
├── server/                 # Node.js Express API server (TypeScript)
│   ├── src/
│   │   ├── index.ts        # Entry point
│   │   ├── app.ts          # Express app setup
│   │   ├── lib/
│   │   │   ├── http.ts     # HTTP client with retry logic
│   │   │   └── logger.ts   # Pino logger
│   │   └── routes/
│   │       ├── health.ts   # Health check
│   │       ├── clipfly.ts  # All Clipfly endpoints
│   │       └── geminigen.ts# All GeminiGen endpoints
│   ├── package.json
│   └── tsconfig.json
│
├── python/                 # Python client & examples
│   ├── client.py           # Reusable AIClient class
│   ├── test_all.py         # Full test suite
│   ├── requirements.txt
│   └── examples/
│       ├── 01_text_to_image.py
│       ├── 02_image_to_image.py
│       ├── 03_image_combination.py
│       ├── 04_text_to_video.py
│       ├── 05_image_to_video.py
│       ├── 06_geminigen_veo_fast.py
│       ├── 07_geminigen_veo_with_image.py
│       └── 08_geminigen_grok.py
│
├── docs/
│   ├── API.md              # Full API reference
│   └── INSTALL.md          # Detailed installation guide
│
├── install.sh              # One-command VPS installer
├── Dockerfile              # Docker image
├── docker-compose.yml      # Docker Compose config
├── ecosystem.config.cjs    # PM2 config
├── .env.example            # Environment variables template
└── README.md               # This file
```

---

## Endpoints Summary

| Method | Endpoint | Body Fields | Returns |
|--------|----------|-------------|---------|
| GET | `/api/healthz` | — | `{status}` |
| POST | `/api/clipfly/text-to-image` | `prompt`, `size_id?` | `{queue_id, token}` |
| POST | `/api/clipfly/image-to-image` | `prompt`, `base64`, `filename?` | `{queue_id, token}` |
| POST | `/api/clipfly/image-combination` | `prompt`, `images[]`, `size_id?` | `{queue_id, token}` |
| POST | `/api/clipfly/text-to-video` | `prompt`, `model?`, `ratio?` | `{queue_id, token}` |
| POST | `/api/clipfly/image-to-video` | `prompt`, `base64`, `model?` | `{queue_id, token}` |
| GET | `/api/clipfly/image-status` | `?queue_id` + `Authorization` header | `{status, url}` |
| GET | `/api/clipfly/video-status` | `?queue_id` + `Authorization` header | `{status, url}` |
| POST | `/api/geminigen/video-gen` | `prompt`, `model?`, `aspect_ratio?`, `images?[]` | `{uuid, access_token}` |
| GET | `/api/geminigen/status/:uuid` | `?access_token` | `{status, video_url}` |

Full reference: [docs/API.md](docs/API.md)

---

## Tech Stack

- **Runtime:** Node.js 20
- **Framework:** Express 4
- **Language:** TypeScript
- **HTTP Client:** Axios (with auto-retry)
- **Process Manager:** PM2
- **Proxy:** Nginx
- **Python Client:** `requests` + `Pillow`

---

## License

MIT
