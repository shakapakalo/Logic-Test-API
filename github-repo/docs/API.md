# API Reference

Base URL: `http://YOUR_VPS_IP/api` (via Nginx) or `http://YOUR_VPS_IP:3000/api` (direct)

---

## Health

### GET `/api/healthz`
Returns server status.

**Response:**
```json
{ "status": "ok", "timestamp": "2025-01-01T00:00:00.000Z" }
```

---

## Clipfly — AI Image Generation

> **Note:** Every endpoint auto-creates a fresh Clipfly account. You do NOT need to register or provide any credentials.

---

### POST `/api/clipfly/text-to-image`
Generate an image from a text prompt.

**Request:**
```json
{
  "prompt": "A sunset over the ocean",
  "size_id": "16:9"
}
```

| Field    | Type   | Required | Description |
|----------|--------|----------|-------------|
| prompt   | string | ✅       | Text description of the image |
| size_id  | string | ❌       | Aspect ratio. Default: `"9:16"` |

**Size options:** `1:1` `9:16` `16:9` `3:4` `4:3` `2:3` `3:2` `21:9`

**Response:**
```json
{ "success": true, "queue_id": 17916116, "token": "Bearer eyJ..." }
```
→ Use `queue_id` + `token` to poll `/api/clipfly/image-status`

---

### POST `/api/clipfly/image-to-image`
Transform an existing image using a prompt.

**Request:**
```json
{
  "prompt": "Anime art style with vibrant colors",
  "base64": "<base64 encoded JPEG/PNG>",
  "filename": "photo.jpg"
}
```

| Field    | Type   | Required | Description |
|----------|--------|----------|-------------|
| prompt   | string | ✅       | Transformation description |
| base64   | string | ✅       | Base64 encoded image (JPEG or PNG) |
| filename | string | ❌       | Original filename. Default: `"image.jpg"` |

**Response:** Same as text-to-image.

---

### POST `/api/clipfly/image-combination`
Combine 2 or more images into one.

**Request:**
```json
{
  "prompt": "Blend into a cinematic scene",
  "images": [
    { "base64": "<base64>", "filename": "img1.jpg" },
    { "base64": "<base64>", "filename": "img2.jpg" }
  ],
  "size_id": "1:1"
}
```

| Field    | Type   | Required | Description |
|----------|--------|----------|-------------|
| prompt   | string | ✅       | How to combine the images |
| images   | array  | ✅       | Array of `{base64, filename}` objects (min 2) |
| size_id  | string | ❌       | Output aspect ratio. Default: `"1:1"` |

**Response:** Same as text-to-image.

---

### POST `/api/clipfly/text-to-video`
Generate a video from a text prompt.

**Request:**
```json
{
  "prompt": "Eagle soaring over mountains",
  "model": "wan",
  "ratio": "16:9"
}
```

| Field  | Type   | Required | Description |
|--------|--------|----------|-------------|
| prompt | string | ✅       | Video description |
| model  | string | ❌       | `"wan"` (10s) or `"seedance"` (5s). Default: `"wan"` |
| ratio  | string | ❌       | `"16:9"`, `"9:16"`, `"1:1"`. Default: `"16:9"` |
| audio  | string | ❌       | Optional audio/voice prompt |

**Response:**
```json
{ "success": true, "queue_id": "abc123", "token": "Bearer eyJ..." }
```
→ Use `queue_id` + `token` to poll `/api/clipfly/video-status`

---

### POST `/api/clipfly/image-to-video`
Animate an image into a video.

**Request:**
```json
{
  "prompt": "The scene comes alive with gentle motion",
  "base64": "<base64 encoded image>",
  "filename": "scene.jpg",
  "model": "wan"
}
```

| Field    | Type   | Required | Description |
|----------|--------|----------|-------------|
| prompt   | string | ✅       | Animation description |
| base64   | string | ✅       | Base64 encoded image |
| filename | string | ❌       | Filename. Default: `"image.jpg"` |
| model    | string | ❌       | `"wan"`, `"seedance"`, or `"lumen"`. Default: `"wan"` |
| audio    | string | ❌       | Optional audio prompt |

**Response:** Same as text-to-video.

---

### GET `/api/clipfly/image-status`
Check the status of an image generation task.

**Headers:** `Authorization: <token from POST response>`

**Query params:** `?queue_id=<id>`

**Response:**
```json
{ "success": true, "status": "completed", "url": "https://www.clipfly.ai/..." }
```

| Status       | Description |
|--------------|-------------|
| `"pending"`  | Still processing |
| `"completed"`| Done — `url` contains the image URL |
| `"failed"`   | Failed — `reason` contains the error |

---

### GET `/api/clipfly/video-status`
Check the status of a video generation task.

**Headers:** `Authorization: <token from POST response>`

**Query params:** `?queue_id=<id>`

**Response:**
```json
{ "success": true, "status": "completed", "url": "https://www.clipfly.ai/..." }
```

---

## GeminiGen — AI Video Generation (Veo & Grok)

> **Note:** Every call auto-creates a fresh GeminiGen account. No credentials needed.

---

### POST `/api/geminigen/video-gen`
Generate a video using Veo or Grok model.

**Request:**
```json
{
  "prompt": "A futuristic city at night with neon lights",
  "model": "veo_fast",
  "aspect_ratio": "16:9",
  "images": []
}
```

| Field        | Type   | Required | Description |
|--------------|--------|----------|-------------|
| prompt       | string | ✅       | Video description |
| model        | string | ❌       | `"veo_fast"`, `"veo_lite"`, or `"grok"`. Default: `"veo_fast"` |
| aspect_ratio | string | ❌       | `"16:9"`, `"9:16"`, `"1:1"`. Default: `"16:9"` |
| images       | array  | ❌       | Optional `[{base64, filename}]`. Veo: 1 image max. Grok: up to 3 images |

**Models:**
| Model       | Duration | Best For |
|-------------|----------|----------|
| `veo_fast`  | 8s       | Fast generation, text or image input |
| `veo_lite`  | 8s       | Lighter model, text or image input |
| `grok`      | 10s      | Up to 3 input images |

**Response:**
```json
{ "success": true, "uuid": "abc-123-...", "access_token": "eyJ..." }
```
→ Use `uuid` + `access_token` to poll `/api/geminigen/status/:uuid`

---

### GET `/api/geminigen/status/:uuid`
Check the status of a GeminiGen video task.

**Query params:** `?access_token=<token from POST response>`

**Response:**
```json
{ "success": true, "status": "completed", "video_url": "https://..." }
```

| Status       | Description |
|--------------|-------------|
| `"pending"`  | Still processing |
| `"completed"`| Done — `video_url` contains the video URL |
| `"failed"`   | Failed — `reason` contains the error |
