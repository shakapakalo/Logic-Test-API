# 🤖 AI API Server

> **Clipfly** (AI Image & Video) + **GeminiGen** (Veo & Grok Video) — Professional REST API  
> Every request **auto-creates a fresh account** — no API keys, no sign-ups needed.

---

## 📋 Table of Contents

- [Features](#features)
- [Install on Contabo VPS](#install-on-contabo-vps)
- [Install with Docker](#install-with-docker)
- [Python Usage](#python-usage)
- [API Reference](#api-reference)
- [All Python Examples](#all-python-examples)
- [Troubleshooting](#troubleshooting)

---

## ✨ Features

| Service | What it does | Endpoint |
|---------|-------------|----------|
| Clipfly | Text → Image | `POST /api/clipfly/text-to-image` |
| Clipfly | Image → Image | `POST /api/clipfly/image-to-image` |
| Clipfly | Combine Images | `POST /api/clipfly/image-combination` |
| Clipfly | Text → Video | `POST /api/clipfly/text-to-video` |
| Clipfly | Image → Video | `POST /api/clipfly/image-to-video` |
| GeminiGen | Veo Fast (text/image → video) | `POST /api/geminigen/video-gen` |
| GeminiGen | Veo Lite (text/image → video) | `POST /api/geminigen/video-gen` |
| GeminiGen | Grok (1–3 images → video) | `POST /api/geminigen/video-gen` |

---

## 🖥️ Install on Contabo VPS

> Tested on Ubuntu 20.04 / 22.04 / 24.04

### Step 1 — Connect to your VPS

```bash
ssh root@YOUR_VPS_IP
```

### Step 2 — Update the system

```bash
apt-get update && apt-get upgrade -y
apt-get install -y curl wget git build-essential nginx ufw
```

### Step 3 — Install Node.js 20

```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt-get install -y nodejs

# Verify
node -v    # Should show v20.x.x
npm -v     # Should show 10.x.x
```

### Step 4 — Install PM2 (process manager)

```bash
npm install -g pm2
```

### Step 5 — Clone this repo

```bash
cd /root
git clone https://github.com/YOUR_GITHUB_USERNAME/ai-api-server.git
cd ai-api-server
```

### Step 6 — Build the server

```bash
cd server
npm install
npm run build
cd ..
```

### Step 7 — Start the server

```bash
# Copy environment config
cp .env.example .env

# Start with PM2 on port 3000
PORT=3000 pm2 start server/dist/index.js --name "ai-api"

# Save PM2 so it restarts after reboot
pm2 save
pm2 startup
# Copy and run the command it shows you
```

### Step 8 — Configure Nginx (port 80)

```bash
cat > /etc/nginx/sites-available/ai-api << 'EOF'
server {
    listen 80;
    server_name _;
    client_max_body_size 100M;

    location /api {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }
}
EOF

ln -sf /etc/nginx/sites-available/ai-api /etc/nginx/sites-enabled/ai-api
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl restart nginx && systemctl enable nginx
```

### Step 9 — Open firewall

```bash
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 3000/tcp
ufw --force enable
```

### Step 10 — Test it works

```bash
curl http://localhost:3000/api/healthz
# Expected: {"status":"ok","timestamp":"..."}

curl http://YOUR_VPS_IP/api/healthz
# Same result via Nginx
```

---

## 🐳 Install with Docker

> Much easier — just 3 commands

```bash
# Clone the repo
git clone https://github.com/YOUR_GITHUB_USERNAME/ai-api-server.git
cd ai-api-server

# Start
docker compose up -d

# Check it's running
curl http://localhost:3000/api/healthz
```

---

## 🐍 Python Usage

### Install Python requirements

```bash
cd python
pip install -r requirements.txt
```

`requirements.txt`:
```
requests>=2.31.0
Pillow>=10.0.0
```

### Use the Client Library

```python
from client import AIClient

# Point to your VPS
client = AIClient("http://YOUR_VPS_IP/api")
# or for local testing:
# client = AIClient("http://localhost:3000/api")

# Check server is running
print(client.health())  # True
```

---

## 📡 API Reference

### Base URL
```
http://YOUR_VPS_IP/api          (via Nginx, port 80)
http://YOUR_VPS_IP:3000/api     (direct)
```

---

### GET `/api/healthz`
Check if server is running.

```bash
curl http://YOUR_VPS_IP/api/healthz
```
```json
{"status": "ok", "timestamp": "2025-01-01T00:00:00.000Z"}
```

---

### POST `/api/clipfly/text-to-image`

Generate an image from text. **Auto-creates account.**

```bash
curl -X POST http://YOUR_VPS_IP/api/clipfly/text-to-image \
  -H "Content-Type: application/json" \
  -d '{"prompt": "A sunset over the ocean", "size_id": "16:9"}'
```

**Request body:**
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `prompt` | string | ✅ | — | Image description |
| `size_id` | string | ❌ | `"9:16"` | `1:1` `9:16` `16:9` `3:4` `4:3` `2:3` `3:2` `21:9` |

**Response:**
```json
{
  "success": true,
  "queue_id": 17916116,
  "token": "Bearer eyJ..."
}
```
→ Use `queue_id` + `token` → poll `GET /api/clipfly/image-status`

---

### POST `/api/clipfly/image-to-image`

Transform an image using a prompt. **Auto-creates account + uploads image.**

```bash
curl -X POST http://YOUR_VPS_IP/api/clipfly/image-to-image \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Anime art style",
    "base64": "<BASE64_IMAGE>",
    "filename": "photo.jpg"
  }'
```

**Request body:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `prompt` | string | ✅ | Transformation description |
| `base64` | string | ✅ | Base64 encoded image (JPEG or PNG) |
| `filename` | string | ❌ | File name (default: `image.jpg`) |

**Response:** Same as text-to-image → poll `GET /api/clipfly/image-status`

---

### POST `/api/clipfly/image-combination`

Combine 2 or more images into one. **Auto-creates account.**

```bash
curl -X POST http://YOUR_VPS_IP/api/clipfly/image-combination \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Blend into one cinematic scene",
    "images": [
      {"base64": "<BASE64_1>", "filename": "img1.jpg"},
      {"base64": "<BASE64_2>", "filename": "img2.jpg"}
    ],
    "size_id": "1:1"
  }'
```

**Request body:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `prompt` | string | ✅ | How to combine images |
| `images` | array | ✅ | Array of `{base64, filename}` — minimum 2 |
| `size_id` | string | ❌ | Output size (default: `"1:1"`) |

**Response:** Same format → poll `GET /api/clipfly/image-status`

---

### POST `/api/clipfly/text-to-video`

Generate a video from text. **Auto-creates account.**

```bash
curl -X POST http://YOUR_VPS_IP/api/clipfly/text-to-video \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Eagle soaring over mountains", "model": "wan", "ratio": "16:9"}'
```

**Request body:**
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `prompt` | string | ✅ | — | Video description |
| `model` | string | ❌ | `"wan"` | `"wan"` (10s) or `"seedance"` (5s) |
| `ratio` | string | ❌ | `"16:9"` | `"16:9"` `"9:16"` `"1:1"` |
| `audio` | string | ❌ | `""` | Optional audio prompt |

**Response:**
```json
{"success": true, "queue_id": "abc123", "token": "Bearer eyJ..."}
```
→ Poll `GET /api/clipfly/video-status`

---

### POST `/api/clipfly/image-to-video`

Animate an image into a video. **Auto-creates account + uploads image.**

```bash
curl -X POST http://YOUR_VPS_IP/api/clipfly/image-to-video \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Cinematic slow camera movement",
    "base64": "<BASE64_IMAGE>",
    "filename": "scene.jpg",
    "model": "wan"
  }'
```

**Request body:**
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `prompt` | string | ✅ | — | Animation description |
| `base64` | string | ✅ | — | Base64 image |
| `filename` | string | ❌ | `"image.jpg"` | File name |
| `model` | string | ❌ | `"wan"` | `"wan"` `"seedance"` `"lumen"` |

**Response:** Same as text-to-video → poll `GET /api/clipfly/video-status`

---

### GET `/api/clipfly/image-status`

Poll image task status.

```bash
curl http://YOUR_VPS_IP/api/clipfly/image-status?queue_id=17916116 \
  -H "Authorization: Bearer eyJ..."
```

**Response:**
```json
{"success": true, "status": "completed", "url": "https://www.clipfly.ai/...jpg"}
```

| `status` | Meaning |
|----------|---------|
| `"pending"` | Still processing, poll again |
| `"completed"` | Done — `url` has the image link |
| `"failed"` | Failed — `reason` has the error |

---

### GET `/api/clipfly/video-status`

Poll video task status.

```bash
curl http://YOUR_VPS_IP/api/clipfly/video-status?queue_id=abc123 \
  -H "Authorization: Bearer eyJ..."
```

**Response:**
```json
{"success": true, "status": "completed", "url": "https://www.clipfly.ai/...mp4"}
```

---

### POST `/api/geminigen/video-gen`

Generate video with Veo or Grok. **Auto-creates account.**

```bash
# Text to video
curl -X POST http://YOUR_VPS_IP/api/geminigen/video-gen \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Neon city at night", "model": "veo_fast", "aspect_ratio": "16:9"}'

# Image to video (add images array)
curl -X POST http://YOUR_VPS_IP/api/geminigen/video-gen \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Epic cinematic motion",
    "model": "veo_fast",
    "aspect_ratio": "16:9",
    "images": [{"base64": "<BASE64>", "filename": "photo.jpg"}]
  }'
```

**Request body:**
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `prompt` | string | ✅ | — | Video description |
| `model` | string | ❌ | `"veo_fast"` | `"veo_fast"` `"veo_lite"` `"grok"` |
| `aspect_ratio` | string | ❌ | `"16:9"` | `"16:9"` `"9:16"` `"1:1"` |
| `images` | array | ❌ | `[]` | `[{base64, filename}]` — Veo: max 1, Grok: max 3 |

**Models:**
| Model | Duration | Input |
|-------|----------|-------|
| `veo_fast` | 8s | Text only or + 1 image |
| `veo_lite` | 8s | Text only or + 1 image |
| `grok` | 10s | Text + 1 to 3 images |

**Response:**
```json
{"success": true, "uuid": "abc-123-...", "access_token": "eyJ..."}
```
→ Poll `GET /api/geminigen/status/:uuid`

---

### GET `/api/geminigen/status/:uuid`

Poll GeminiGen video task status.

```bash
curl "http://YOUR_VPS_IP/api/geminigen/status/abc-123?access_token=eyJ..."
```

**Response:**
```json
{"success": true, "status": "completed", "video_url": "https://....mp4"}
```

---

## 🐍 All Python Examples

### Install

```bash
cd python
pip install -r requirements.txt
```

---

### Example 1 — Text to Image

```python
import requests, time

BASE = "http://YOUR_VPS_IP/api"

r = requests.post(f"{BASE}/clipfly/text-to-image", json={
    "prompt": "A stunning sunset over the ocean with golden reflections",
    "size_id": "16:9"  # 1:1 | 9:16 | 16:9 | 3:4 | 4:3
})
d = r.json()
print("Submitted:", d["queue_id"])

# Poll until done
while True:
    s = requests.get(f"{BASE}/clipfly/image-status",
        params={"queue_id": d["queue_id"]},
        headers={"Authorization": d["token"]}).json()
    print("Status:", s["status"])
    if s["status"] == "completed":
        print("Image URL:", s["url"])
        break
    elif s["status"] == "failed":
        print("Failed:", s.get("reason"))
        break
    time.sleep(5)
```

---

### Example 2 — Image to Image

```python
import requests, base64, time

BASE = "http://YOUR_VPS_IP/api"

# Load your image as base64
with open("my_photo.jpg", "rb") as f:
    b64 = base64.b64encode(f.read()).decode()

r = requests.post(f"{BASE}/clipfly/image-to-image", json={
    "prompt": "Transform into anime art style with vibrant neon colors",
    "base64": b64,
    "filename": "my_photo.jpg"
})
d = r.json()
print("Submitted:", d["queue_id"])

# Poll
while True:
    s = requests.get(f"{BASE}/clipfly/image-status",
        params={"queue_id": d["queue_id"]},
        headers={"Authorization": d["token"]}).json()
    print("Status:", s["status"])
    if s["status"] == "completed":
        print("Image URL:", s["url"])
        break
    time.sleep(5)
```

---

### Example 3 — Image Combination (2+ images)

```python
import requests, base64, time

BASE = "http://YOUR_VPS_IP/api"

with open("photo1.jpg", "rb") as f: b64_1 = base64.b64encode(f.read()).decode()
with open("photo2.jpg", "rb") as f: b64_2 = base64.b64encode(f.read()).decode()

r = requests.post(f"{BASE}/clipfly/image-combination", json={
    "prompt": "Blend these into one artistic cinematic composition",
    "images": [
        {"base64": b64_1, "filename": "photo1.jpg"},
        {"base64": b64_2, "filename": "photo2.jpg"}
    ],
    "size_id": "1:1"
})
d = r.json()

while True:
    s = requests.get(f"{BASE}/clipfly/image-status",
        params={"queue_id": d["queue_id"]},
        headers={"Authorization": d["token"]}).json()
    if s["status"] == "completed":
        print("Combined Image:", s["url"]); break
    time.sleep(5)
```

---

### Example 4 — Text to Video

```python
import requests, time

BASE = "http://YOUR_VPS_IP/api"

r = requests.post(f"{BASE}/clipfly/text-to-video", json={
    "prompt": "An eagle soaring majestically over snow-capped mountains at golden hour",
    "model": "wan",    # "wan" (10s) or "seedance" (5s)
    "ratio": "16:9"   # "16:9", "9:16", "1:1"
})
d = r.json()
print("Submitted:", d["queue_id"])

# Poll video status (use video-status not image-status)
while True:
    s = requests.get(f"{BASE}/clipfly/video-status",
        params={"queue_id": d["queue_id"]},
        headers={"Authorization": d["token"]}).json()
    print("Status:", s["status"])
    if s["status"] == "completed":
        print("Video URL:", s["url"]); break
    elif s["status"] == "failed":
        print("Failed:", s.get("reason")); break
    time.sleep(5)
```

---

### Example 5 — Image to Video

```python
import requests, base64, time

BASE = "http://YOUR_VPS_IP/api"

with open("my_photo.jpg", "rb") as f:
    b64 = base64.b64encode(f.read()).decode()

r = requests.post(f"{BASE}/clipfly/image-to-video", json={
    "prompt": "The scene comes alive with gentle slow camera pan and dramatic lighting",
    "base64": b64,
    "filename": "my_photo.jpg",
    "model": "wan"   # "wan", "seedance", or "lumen"
})
d = r.json()

while True:
    s = requests.get(f"{BASE}/clipfly/video-status",
        params={"queue_id": d["queue_id"]},
        headers={"Authorization": d["token"]}).json()
    print("Status:", s["status"])
    if s["status"] == "completed":
        print("Video URL:", s["url"]); break
    time.sleep(5)
```

---

### Example 6 — GeminiGen Veo Fast (Text to Video)

```python
import requests, time

BASE = "http://YOUR_VPS_IP/api"

r = requests.post(f"{BASE}/geminigen/video-gen", json={
    "prompt": "A futuristic city at night with neon lights reflecting on wet streets",
    "model": "veo_fast",    # "veo_fast" or "veo_lite"
    "aspect_ratio": "16:9"  # "16:9", "9:16", "1:1"
})
d = r.json()
print("UUID:", d["uuid"])

while True:
    s = requests.get(f"{BASE}/geminigen/status/{d['uuid']}",
        params={"access_token": d["access_token"]}).json()
    print("Status:", s["status"])
    if s["status"] == "completed":
        print("Video URL:", s["video_url"]); break
    elif s["status"] == "failed":
        print("Failed:", s.get("reason")); break
    time.sleep(10)
```

---

### Example 7 — GeminiGen Veo + Image (Image to Video)

```python
import requests, base64, time

BASE = "http://YOUR_VPS_IP/api"

with open("scene.jpg", "rb") as f:
    b64 = base64.b64encode(f.read()).decode()

r = requests.post(f"{BASE}/geminigen/video-gen", json={
    "prompt": "This scene bursts into life with dramatic slow motion and epic scale",
    "model": "veo_fast",
    "aspect_ratio": "16:9",
    "images": [{"base64": b64, "filename": "scene.jpg"}]
})
d = r.json()

while True:
    s = requests.get(f"{BASE}/geminigen/status/{d['uuid']}",
        params={"access_token": d["access_token"]}).json()
    if s["status"] == "completed":
        print("Video URL:", s["video_url"]); break
    time.sleep(10)
```

---

### Example 8 — GeminiGen Grok (1–3 Images to Video)

```python
import requests, base64, time

BASE = "http://YOUR_VPS_IP/api"

# Grok supports up to 3 images
images = []
for path in ["photo1.jpg", "photo2.jpg"]:  # add photo3.jpg optionally
    with open(path, "rb") as f:
        images.append({"base64": base64.b64encode(f.read()).decode(), "filename": path})

r = requests.post(f"{BASE}/geminigen/video-gen", json={
    "prompt": "The images transform with surreal floating elements and epic cinematic scale",
    "model": "grok",
    "aspect_ratio": "16:9",
    "images": images
})
d = r.json()

while True:
    s = requests.get(f"{BASE}/geminigen/status/{d['uuid']}",
        params={"access_token": d["access_token"]}).json()
    if s["status"] == "completed":
        print("Video URL:", s["video_url"]); break
    time.sleep(10)
```

---

### Run Full Test Suite

```bash
cd python
python3 test_all.py http://YOUR_VPS_IP/api
```

---

## 🔧 Server Management

```bash
# Check server status
pm2 status

# View live logs
pm2 logs ai-api

# Restart server
pm2 restart ai-api

# Stop server
pm2 stop ai-api

# Update to latest code
git pull origin main
cd server && npm install && npm run build && cd ..
pm2 restart ai-api
```

---

## ❗ Troubleshooting

### Server won't start
```bash
pm2 logs ai-api --lines 50
# Check for errors in the output
```

### Port 3000 already in use
```bash
sudo lsof -i :3000
# Change PORT in .env and restart
```

### Nginx not working
```bash
sudo nginx -t          # Test config
sudo systemctl status nginx
sudo journalctl -u nginx -n 30
```

### Python: Connection refused
```bash
# Make sure server is running
pm2 status
# Make sure port 3000 is open
curl http://localhost:3000/api/healthz
```

### Build errors
```bash
cd server
rm -rf node_modules dist
npm install
npm run build
```

---

## 📁 Project Structure

```
ai-api-server/
├── server/                    ← Node.js API server (TypeScript)
│   ├── src/
│   │   ├── index.ts           ← Entry point
│   │   ├── app.ts             ← Express setup
│   │   ├── lib/
│   │   │   ├── http.ts        ← HTTP client with auto-retry
│   │   │   └── logger.ts      ← Logger
│   │   └── routes/
│   │       ├── health.ts      ← Health check
│   │       ├── clipfly.ts     ← All Clipfly endpoints
│   │       └── geminigen.ts   ← All GeminiGen endpoints
│   ├── package.json
│   └── tsconfig.json
│
├── python/                    ← Python client & examples
│   ├── client.py              ← Reusable AIClient class
│   ├── test_all.py            ← Full test suite (10 tests)
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
├── install.sh                 ← One-command VPS installer
├── Dockerfile                 ← Docker image
├── docker-compose.yml         ← Docker Compose
├── ecosystem.config.cjs       ← PM2 config
├── .env.example               ← Environment config template
└── README.md                  ← This file
```

---

## ⚙️ Environment Variables

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

```env
PORT=3000
NODE_ENV=production
LOG_LEVEL=info
```

---

## 🔗 Tech Stack

- **Node.js 20** + **TypeScript**
- **Express 4** — HTTP framework
- **Axios** — HTTP client with retry logic
- **PM2** — Process manager
- **Nginx** — Reverse proxy
- **Python 3** — Client library and examples
