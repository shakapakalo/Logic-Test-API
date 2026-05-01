import { Router } from "express";
import type { Request, Response } from "express";
import { randomUUID } from "crypto";
import axios from "axios";
import FormData from "form-data";
import { geminiHeaders, GEMINIGEN_BASE } from "../lib/http.js";

const router = Router();
const GEMINIGEN_XTOKEN = "7822db02280a28d61d6a75d199af010e";

function generateDeviceToken(): string {
  const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_";
  const rand = (n: number) => Array.from({ length: n }, () => chars[Math.floor(Math.random() * chars.length)]).join("");
  return `${rand(22)}:${rand(140)}`;
}

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

async function freshGeminiToken(): Promise<string> {
  const url = `${GEMINIGEN_BASE}/mobile/v1/uuid/activate-account`;
  for (let i = 0; i < 10; i++) {
    try {
      const resp = await axios.post(
        url,
        { mobile_device_uuid: randomUUID().replace(/-/g, "").slice(0, 16), platform: "GenV-APP", device_token: generateDeviceToken(), device_type: "android" },
        { headers: { ...geminiHeaders(), "content-type": "application/json", "x-timestamp": String(Math.floor(Date.now() / 1000)), "x-token": GEMINIGEN_XTOKEN }, timeout: 15000 },
      );
      const token = resp.data?.access_token;
      if (token) return token;
    } catch { await sleep(2000); }
  }
  throw new Error("Failed to obtain GeminiGen token after 10 attempts");
}

// POST /api/geminigen/video-gen
// Body: { prompt, model?, aspect_ratio?, images? }
router.post("/video-gen", async (req: Request, res: Response) => {
  const { prompt, model = "veo_fast", aspect_ratio = "16:9", images = [] } = req.body as {
    prompt: string; model?: "veo_fast" | "veo_lite" | "grok"; aspect_ratio?: string;
    images?: Array<{ base64: string; filename?: string }>;
  };
  if (!prompt) { res.status(400).json({ success: false, error: "prompt is required" }); return; }
  try {
    const access_token = await freshGeminiToken();
    for (let attempt = 0; attempt < 10; attempt++) {
      try {
        if (model === "veo_fast" || model === "veo_lite") {
          const form = new FormData();
          form.append("prompt", prompt);
          form.append("model", model === "veo_fast" ? "veo-3.1-fast" : "veo-3.1-lite");
          form.append("duration", "8");
          form.append("resolution", "720p");
          form.append("aspect_ratio", aspect_ratio);
          form.append("service_mode", "stable");
          for (const [i, img] of images.entries()) {
            const buf = Buffer.from(img.base64.replace(/^data:[^;]+;base64,/, ""), "base64");
            form.append("image", buf, { filename: img.filename ?? `image_${i}.jpg`, contentType: "image/jpeg" });
          }
          const resp = await axios.post(`${GEMINIGEN_BASE}/mobile/v3/video-gen`, form, {
            headers: { ...geminiHeaders(access_token), ...form.getHeaders() }, timeout: 30000,
          });
          if (resp.data?.uuid) { res.json({ success: true, uuid: resp.data.uuid, access_token }); return; }

        } else if (model === "grok") {
          const form = new FormData();
          form.append("mode", "custom"); form.append("prompt", prompt); form.append("model", "grok-video");
          form.append("resolution", "720p"); form.append("aspect_ratio", aspect_ratio); form.append("duration", "10");
          form.append("turnstile_token", "string"); form.append("service_mode", "stable");
          for (const [i, img] of images.entries()) {
            const buf = Buffer.from(img.base64.replace(/^data:[^;]+;base64,/, ""), "base64");
            form.append("files", buf, { filename: img.filename ?? `image_${i}.jpg`, contentType: "image/jpeg" });
          }
          const resp = await axios.post(`${GEMINIGEN_BASE}/mobile/v3/video-gen/grok-stream`, form, {
            headers: { ...geminiHeaders(access_token), ...form.getHeaders() }, responseType: "text", timeout: 30000,
          });
          for (const line of String(resp.data).split("\n")) {
            const cleaned = line.startsWith("data: ") ? line.slice(6) : line;
            try {
              const json = JSON.parse(cleaned);
              if (json.history_uuid) { res.json({ success: true, uuid: json.history_uuid, access_token }); return; }
            } catch { /* skip */ }
          }
        }
      } catch { await sleep(3000); }
    }
    res.status(502).json({ success: false, error: "Failed to submit GeminiGen video task after 10 attempts" });
  } catch (err) { res.status(500).json({ success: false, error: String(err) }); }
});

// GET /api/geminigen/status/:uuid?access_token=...
router.get("/status/:uuid", async (req: Request, res: Response) => {
  const { uuid } = req.params;
  const access_token = (req.query.access_token as string) || (req.headers.authorization as string)?.replace("Bearer ", "");
  if (!uuid || !access_token) { res.status(400).json({ success: false, error: "uuid and access_token required" }); return; }
  try {
    const resp = await axios.get(`${GEMINIGEN_BASE}/mobile/v1/history/${uuid}`, {
      headers: geminiHeaders(access_token), timeout: 15000,
    });
    const data = resp.data;
    const status = data?.status;
    if (status === 2) {
      res.json({ success: true, status: "completed", video_url: (data?.generated_video ?? [])[0]?.video_url ?? null });
    } else if ([3, 4, -1].includes(status)) {
      res.json({ success: true, status: "failed", reason: data?.error_message });
    } else {
      res.json({ success: true, status: "pending", raw_status: status });
    }
  } catch (err) { res.status(500).json({ success: false, error: String(err) }); }
});

export default router;
