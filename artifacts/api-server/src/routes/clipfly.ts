import { Router } from "express";
import type { Request, Response } from "express";
import { randomBytes } from "crypto";
import { clipflyHeaders, retryPost, retryGet, CLIPFLY_BASE } from "../lib/http.js";

const router = Router();

const DIMS: Record<string, [number, number]> = {
  "1:1": [2048, 2048],
  "9:16": [1536, 2752],
  "16:9": [2752, 1536],
  "3:4": [1536, 2048],
  "4:3": [2048, 1536],
  "2:3": [1536, 2304],
  "3:2": [2304, 1536],
  "21:9": [3264, 1408],
};

function randomStr(len: number) {
  return randomBytes(len).toString("hex").slice(0, len);
}

/**
 * POST /api/clipfly/register
 * Auto-registers a Clipfly account and returns a token.
 */
router.post("/register", async (req: Request, res: Response) => {
  try {
    const username = randomStr(10);
    const email = `${username}@znsj.com`;
    const password = "User" + randomStr(8) + "!";

    const data = await retryPost<{ code: number; data?: { token?: { token: string } }; msg?: string }>(
      `${CLIPFLY_BASE}/api/v1/account/register`,
      { email, password, ref: null, activity_id: null, invitor_id: null },
      { headers: clipflyHeaders() },
    );

    if (data.code === 0 && data.data?.token?.token) {
      res.json({ success: true, token: data.data.token.token, email, password });
    } else {
      res.status(502).json({ success: false, error: data.msg ?? "Registration failed" });
    }
  } catch (err: unknown) {
    req.log.error(err);
    res.status(500).json({ success: false, error: String(err) });
  }
});

/**
 * POST /api/clipfly/upload
 * Upload a base64-encoded image to Clipfly storage.
 * Body: { token, base64, filename }
 */
router.post("/upload", async (req: Request, res: Response) => {
  const { token, base64, filename = "image.jpg" } = req.body as {
    token: string;
    base64: string;
    filename?: string;
  };

  if (!token || !base64) {
    res.status(400).json({ success: false, error: "token and base64 are required" });
    return;
  }

  const mimeType = filename.endsWith(".png") ? "image/png" : "image/jpeg";
  const content = base64.startsWith("data:") ? base64 : `data:${mimeType};base64,${base64}`;

  try {
    const data = await retryPost<{
      code: number;
      data?: { storage_path: string; user_id?: string };
      msg?: string;
    }>(
      `${CLIPFLY_BASE}/api/v1/common/upload/base64`,
      { content, name: filename, file_type: "image", is_original_name: 0, prefix_path: "/uploads" },
      { headers: clipflyHeaders(token) },
    );

    if (data.code === 0 && data.data?.storage_path) {
      res.json({ success: true, storage_path: data.data.storage_path, user_id: data.data.user_id });
    } else {
      res.status(502).json({ success: false, error: data.msg ?? "Upload failed" });
    }
  } catch (err) {
    req.log.error(err);
    res.status(500).json({ success: false, error: String(err) });
  }
});

/**
 * POST /api/clipfly/text-to-image
 * Generate an image from a text prompt.
 * Body: { token, prompt, size_id? }
 */
router.post("/text-to-image", async (req: Request, res: Response) => {
  const { token, prompt, size_id = "9:16" } = req.body as {
    token: string;
    prompt: string;
    size_id?: string;
  };

  if (!token || !prompt) {
    res.status(400).json({ success: false, error: "token and prompt are required" });
    return;
  }

  const [width, height] = DIMS[size_id] ?? DIMS["9:16"];

  try {
    const data = await retryPost<{
      code: number;
      data?: Array<{ queue_id: string }>;
      msg?: string;
    }>(
      `${CLIPFLY_BASE}/api/v1/user/ai-tasks/image-generator/create`,
      {
        type: 21,
        prompt,
        negative_prompt: "",
        gnum: 1,
        style_id: "",
        size_id,
        model_id: "nanobanana2",
        height,
        width,
        is_scale: 1,
      },
      { headers: clipflyHeaders(token) },
    );

    if (data.code === 0 && data.data?.[0]?.queue_id) {
      res.json({ success: true, queue_id: data.data[0].queue_id });
    } else {
      res.status(502).json({ success: false, error: data.msg ?? "Task submission failed" });
    }
  } catch (err) {
    req.log.error(err);
    res.status(500).json({ success: false, error: String(err) });
  }
});

/**
 * POST /api/clipfly/image-to-image
 * Transform an existing image using a prompt.
 * Body: { token, prompt, source_image (storage_path), material_id }
 */
router.post("/image-to-image", async (req: Request, res: Response) => {
  const { token, prompt, source_image, material_id } = req.body as {
    token: string;
    prompt: string;
    source_image: string;
    material_id: string;
  };

  if (!token || !prompt || !source_image || !material_id) {
    res.status(400).json({ success: false, error: "token, prompt, source_image, and material_id are required" });
    return;
  }

  try {
    const data = await retryPost<{
      code: number;
      data?: Array<{ queue_id: string }>;
      msg?: string;
    }>(
      `${CLIPFLY_BASE}/api/v1/user/ai-tasks/image-generator/create`,
      {
        type: 22,
        prompt,
        gnum: 1,
        source_image,
        materialId: material_id,
        model_id: "nanobanana2",
        is_scale: 1,
      },
      { headers: clipflyHeaders(token) },
    );

    if (data.code === 0 && data.data?.[0]?.queue_id) {
      res.json({ success: true, queue_id: data.data[0].queue_id });
    } else {
      res.status(502).json({ success: false, error: data.msg ?? "Task submission failed" });
    }
  } catch (err) {
    req.log.error(err);
    res.status(500).json({ success: false, error: String(err) });
  }
});

/**
 * POST /api/clipfly/image-combination
 * Combine multiple images with a prompt.
 * Body: { token, prompt, source_images: string[], material_ids: string[], size_id? }
 */
router.post("/image-combination", async (req: Request, res: Response) => {
  const { token, prompt, source_images, material_ids, size_id = "1:1" } = req.body as {
    token: string;
    prompt: string;
    source_images: string[];
    material_ids: string[];
    size_id?: string;
  };

  if (!token || !prompt || !Array.isArray(source_images) || !Array.isArray(material_ids)) {
    res.status(400).json({ success: false, error: "token, prompt, source_images[], and material_ids[] are required" });
    return;
  }

  const [width, height] = DIMS[size_id] ?? DIMS["1:1"];

  try {
    const data = await retryPost<{
      code: number;
      data?: Array<{ queue_id: string }>;
      msg?: string;
    }>(
      `${CLIPFLY_BASE}/api/v1/user/ai-tasks/image-generator/create`,
      {
        type: 47,
        prompt,
        negative_prompt: "",
        gnum: 1,
        size_id,
        source_image: source_images,
        materialId: material_ids,
        model_id: "nanobanana2",
        is_scale: 1,
        width,
        height,
      },
      { headers: clipflyHeaders(token) },
    );

    if (data.code === 0 && data.data?.[0]?.queue_id) {
      res.json({ success: true, queue_id: data.data[0].queue_id });
    } else {
      res.status(502).json({ success: false, error: data.msg ?? "Task submission failed" });
    }
  } catch (err) {
    req.log.error(err);
    res.status(500).json({ success: false, error: String(err) });
  }
});

/**
 * POST /api/clipfly/text-to-video
 * Generate a video from a text prompt.
 * Body: { token, prompt, audio?, model?, ratio? }
 */
router.post("/text-to-video", async (req: Request, res: Response) => {
  const {
    token,
    prompt,
    audio = "",
    model = "wan",
    ratio = "9:16",
  } = req.body as {
    token: string;
    prompt: string;
    audio?: string;
    model?: "seedance" | "wan";
    ratio?: string;
  };

  if (!token || !prompt) {
    res.status(400).json({ success: false, error: "token and prompt are required" });
    return;
  }

  const model_id = model === "seedance" ? "25" : "29";
  const duration = model === "seedance" ? "5" : "10";

  try {
    const data = await retryPost<{
      code: number;
      data?: { id: string };
      msg?: string;
    }>(
      `${CLIPFLY_BASE}/api/v1/user/ai-task-queues`,
      {
        type: 16,
        attrs: [
          {
            camera_control: "auto",
            is_scale: 0,
            prompt,
            enhance: true,
            style: "general",
            negative_prompt: "",
            ratio,
            from: "text",
            voice: audio,
            model_id,
            camerafixed: false,
            duration,
            audio_type: 0,
            biz_type: 16,
          },
        ],
      },
      { headers: clipflyHeaders(token) },
    );

    if (data.code === 0 && data.data?.id) {
      res.json({ success: true, queue_id: data.data.id });
    } else {
      res.status(502).json({ success: false, error: data.msg ?? "Task submission failed" });
    }
  } catch (err) {
    req.log.error(err);
    res.status(500).json({ success: false, error: String(err) });
  }
});

/**
 * POST /api/clipfly/image-to-video
 * Generate a video from an uploaded image.
 * Body: { token, prompt, source_image (storage_path), audio?, model? }
 */
router.post("/image-to-video", async (req: Request, res: Response) => {
  const {
    token,
    prompt,
    source_image,
    audio = "",
    model = "wan",
  } = req.body as {
    token: string;
    prompt: string;
    source_image: string;
    audio?: string;
    model?: "seedance" | "lumen" | "wan";
  };

  if (!token || !prompt || !source_image) {
    res.status(400).json({ success: false, error: "token, prompt, and source_image are required" });
    return;
  }

  let model_id: string;
  let material_id: string;
  const duration = "10";

  if (model === "seedance") {
    model_id = "25"; material_id = "966489002510778368";
  } else if (model === "lumen") {
    model_id = "17"; material_id = "969029917515165696";
  } else {
    model_id = "29"; material_id = "966341557070827520";
  }

  try {
    const data = await retryPost<{
      code: number;
      data?: { id: string };
      msg?: string;
    }>(
      `${CLIPFLY_BASE}/api/v1/user/ai-task-queues`,
      {
        type: 17,
        attrs: [
          {
            maskImage: "",
            prompt,
            camera_control: "auto",
            source_image,
            img_style_id: "111",
            materialId: material_id,
            is_scale: 0,
            negative_prompt: "",
            from: "image",
            urls: { url: source_image },
            voice: audio,
            model_id,
            camerafixed: false,
            duration,
            audio_type: 0,
            biz_type: 17,
          },
        ],
      },
      { headers: clipflyHeaders(token) },
    );

    if (data.code === 0 && data.data?.id) {
      res.json({ success: true, queue_id: data.data.id });
    } else {
      res.status(502).json({ success: false, error: data.msg ?? "Task submission failed" });
    }
  } catch (err) {
    req.log.error(err);
    res.status(500).json({ success: false, error: String(err) });
  }
});

/**
 * GET /api/clipfly/image-status?queue_id=...
 * Poll the status of an image generation task.
 */
router.get("/image-status", async (req: Request, res: Response) => {
  const { queue_id, token } = req.query as { queue_id: string; token: string };

  if (!queue_id || !token) {
    res.status(400).json({ success: false, error: "queue_id and token are required" });
    return;
  }

  try {
    const data = await retryGet<{
      code: number;
      data?: Array<{
        status?: number;
        fail_reason?: string;
        after_material?: { urls: { url: string } };
      }>;
      msg?: string;
    }>(
      `${CLIPFLY_BASE}/api/v1/user/ai-tasks/image-generator/queue-detail?queue_id=${queue_id}`,
      { headers: clipflyHeaders(token) },
    );

    if (data.code === 0 && data.data?.[0]) {
      const info = data.data[0];
      if (info.after_material) {
        res.json({ success: true, status: "completed", url: `${CLIPFLY_BASE}${info.after_material.urls.url}` });
      } else if (info.status === 3) {
        res.json({ success: true, status: "failed", reason: info.fail_reason });
      } else {
        res.json({ success: true, status: "pending" });
      }
    } else {
      res.status(502).json({ success: false, error: data.msg ?? "Status check failed" });
    }
  } catch (err) {
    req.log.error(err);
    res.status(500).json({ success: false, error: String(err) });
  }
});

/**
 * GET /api/clipfly/video-status?queue_id=...
 * Poll the status of a video generation task.
 */
router.get("/video-status", async (req: Request, res: Response) => {
  const { queue_id, token } = req.query as { queue_id: string; token: string };

  if (!queue_id || !token) {
    res.status(400).json({ success: false, error: "queue_id and token are required" });
    return;
  }

  try {
    const data = await retryGet<{
      code: number;
      data?: Array<{
        status: number;
        fail_reason?: string;
        ext?: { output_path: string };
      }>;
      msg?: string;
    }>(
      `${CLIPFLY_BASE}/api/v1/user/ai-task-queues?queue_id=${queue_id}`,
      { headers: clipflyHeaders(token) },
    );

    if (data.code === 0 && data.data?.[0]) {
      const info = data.data[0];
      if (info.status === 2 && info.ext?.output_path) {
        res.json({ success: true, status: "completed", url: `${CLIPFLY_BASE}${info.ext.output_path}` });
      } else if (info.status === 3) {
        res.json({ success: true, status: "failed", reason: info.fail_reason });
      } else {
        res.json({ success: true, status: "pending", raw_status: info.status });
      }
    } else {
      res.status(502).json({ success: false, error: data.msg ?? "Status check failed" });
    }
  } catch (err) {
    req.log.error(err);
    res.status(500).json({ success: false, error: String(err) });
  }
});

export default router;
