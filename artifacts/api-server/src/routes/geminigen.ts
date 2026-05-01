import { Router } from "express";
import type { Request, Response } from "express";
import { randomUUID } from "crypto";
import axios from "axios";
import FormData from "form-data";
import { geminiHeaders, GEMINIGEN_BASE } from "../lib/http.js";

const router = Router();

const GEMINIGEN_XTOKEN = "7822db02280a28d61d6a75d199af010e";

/**
 * POST /api/geminigen/token
 * Activate a new GeminiGen account and return an access token.
 */
router.post("/token", async (req: Request, res: Response) => {
  const url = `${GEMINIGEN_BASE}/mobile/v1/uuid/activate-account`;

  for (let i = 0; i < 10; i++) {
    try {
      const timestamp = String(Math.floor(Date.now() / 1000));
      const deviceToken = generateDeviceToken();
      const resp = await axios.post(
        url,
        {
          mobile_device_uuid: randomUUID().replace(/-/g, "").slice(0, 16),
          platform: "GenV-APP",
          device_token: deviceToken,
          device_type: "android",
        },
        {
          headers: {
            ...geminiHeaders(),
            "content-type": "application/json",
            "x-timestamp": timestamp,
            "x-token": GEMINIGEN_XTOKEN,
          },
          timeout: 15000,
        },
      );

      const token = resp.data?.access_token;
      if (token) {
        res.json({ success: true, access_token: token });
        return;
      }
    } catch {
      await sleep(2000);
    }
  }

  res.status(502).json({ success: false, error: "Failed to obtain GeminiGen token after 10 attempts" });
});

/**
 * POST /api/geminigen/video-gen
 * Generate a video using Veo or Grok model.
 * Body: {
 *   access_token,
 *   prompt,
 *   model: "veo_fast" | "veo_lite" | "grok",
 *   aspect_ratio?: "16:9" | "9:16" | "1:1",
 *   images?: [{ base64: string, filename: string }]  // optional, up to 3 for grok
 * }
 */
router.post("/video-gen", async (req: Request, res: Response) => {
  const {
    access_token,
    prompt,
    model = "veo_fast",
    aspect_ratio = "16:9",
    images = [],
  } = req.body as {
    access_token: string;
    prompt: string;
    model?: "veo_fast" | "veo_lite" | "grok";
    aspect_ratio?: string;
    images?: Array<{ base64: string; filename: string }>;
  };

  if (!access_token || !prompt) {
    res.status(400).json({ success: false, error: "access_token and prompt are required" });
    return;
  }

  for (let attempt = 0; attempt < 10; attempt++) {
    try {
      if (model === "veo_fast" || model === "veo_lite") {
        const modelPayload = model === "veo_fast" ? "veo-3.1-fast" : "veo-3.1-lite";
        const url = `${GEMINIGEN_BASE}/mobile/v3/video-gen`;

        const form = new FormData();
        form.append("prompt", prompt);
        form.append("model", modelPayload);
        form.append("duration", "8");
        form.append("resolution", "720p");
        form.append("aspect_ratio", aspect_ratio);
        form.append("service_mode", "stable");

        for (const img of images) {
          const buf = Buffer.from(img.base64.replace(/^data:[^;]+;base64,/, ""), "base64");
          form.append("image", buf, { filename: img.filename, contentType: "image/jpeg" });
        }

        const resp = await axios.post(url, form, {
          headers: { ...geminiHeaders(access_token), ...form.getHeaders() },
          timeout: 30000,
        });

        const uuid = resp.data?.uuid;
        if (uuid) {
          res.json({ success: true, uuid });
          return;
        }
      } else if (model === "grok") {
        const url = `${GEMINIGEN_BASE}/mobile/v3/video-gen/grok-stream`;

        const form = new FormData();
        form.append("mode", "custom");
        form.append("prompt", prompt);
        form.append("model", "grok-video");
        form.append("resolution", "720p");
        form.append("aspect_ratio", aspect_ratio);
        form.append("duration", "10");
        form.append("turnstile_token", "string");
        form.append("service_mode", "stable");

        for (const img of images) {
          const buf = Buffer.from(img.base64.replace(/^data:[^;]+;base64,/, ""), "base64");
          form.append("files", buf, { filename: img.filename, contentType: "image/jpeg" });
        }

        const resp = await axios.post(url, form, {
          headers: { ...geminiHeaders(access_token), ...form.getHeaders() },
          responseType: "text",
          timeout: 30000,
        });

        const lines = String(resp.data).split("\n");
        let found: string | null = null;
        for (const line of lines) {
          const cleaned = line.startsWith("data: ") ? line.slice(6) : line;
          try {
            const json = JSON.parse(cleaned);
            if (json.history_uuid) { found = json.history_uuid; break; }
          } catch { /* skip */ }
        }

        if (found) {
          res.json({ success: true, uuid: found });
          return;
        }
      }
    } catch (err) {
      req.log.warn({ attempt, err }, "geminigen video-gen attempt failed");
      await sleep(3000);
    }
  }

  res.status(502).json({ success: false, error: "Failed to submit GeminiGen video task after 10 attempts" });
});

/**
 * GET /api/geminigen/status/:uuid
 * Check the status of a GeminiGen video generation task.
 * Query: ?access_token=...
 */
router.get("/status/:uuid", async (req: Request, res: Response) => {
  const { uuid } = req.params;
  const { access_token } = req.query as { access_token: string };

  if (!uuid || !access_token) {
    res.status(400).json({ success: false, error: "uuid and access_token are required" });
    return;
  }

  try {
    const resp = await axios.get(`${GEMINIGEN_BASE}/mobile/v1/history/${uuid}`, {
      headers: geminiHeaders(access_token),
      timeout: 15000,
    });

    const data = resp.data;
    const status = data?.status;

    if (status === 2) {
      const videos = data?.generated_video ?? [];
      const video_url = videos[0]?.video_url ?? null;
      res.json({ success: true, status: "completed", video_url });
    } else if ([3, 4, -1].includes(status)) {
      res.json({ success: true, status: "failed", reason: data?.error_message });
    } else {
      res.json({ success: true, status: "pending", raw_status: status });
    }
  } catch (err) {
    req.log.error(err);
    res.status(500).json({ success: false, error: String(err) });
  }
});

function generateDeviceToken(): string {
  const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_";
  const rand = (n: number) => Array.from({ length: n }, () => chars[Math.floor(Math.random() * chars.length)]).join("");
  return `${rand(22)}:${rand(140)}`;
}

function sleep(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}

export default router;
