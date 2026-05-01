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

// ─── Internal helpers ─────────────────────────────────────────────────────────

async function freshToken(): Promise<string> {
  for (let i = 0; i < 10; i++) {
    try {
      const username = randomBytes(6).toString("hex");
      const email = `${username}@znsj.com`;
      const password = "User" + randomBytes(5).toString("hex") + "!";
      const data = await retryPost<{ code: number; data?: { token?: { token: string } } }>(
        `${CLIPFLY_BASE}/api/v1/account/register`,
        { email, password, ref: null, activity_id: null, invitor_id: null },
        { headers: clipflyHeaders() },
        1,
      );
      if (data.code === 0 && data.data?.token?.token) {
        return data.data.token.token;
      }
    } catch {
      /* retry */
    }
  }
  throw new Error("Failed to auto-register Clipfly account after 10 attempts");
}

async function uploadImage(
  base64: string,
  filename: string,
  token: string,
): Promise<{ storage_path: string; material_id: string }> {
  const mimeType = filename.endsWith(".png") ? "image/png" : "image/jpeg";
  const content = base64.startsWith("data:") ? base64 : `data:${mimeType};base64,${base64}`;

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
    return {
      storage_path: data.data.storage_path,
      material_id: String(data.data.user_id ?? data.data.storage_path.split("/")[3]),
    };
  }
  throw new Error(data.msg ?? "Image upload failed");
}

// ─── Routes ───────────────────────────────────────────────────────────────────

/**
 * POST /api/clipfly/text-to-image
 * Auto-creates a new account each call.
 * Body: { prompt, size_id? }
 * Returns: { success, queue_id, token }
 */
router.post("/text-to-image", async (req: Request, res: Response) => {
  const { prompt, size_id = "9:16" } = req.body as {
    prompt: string;
    size_id?: string;
  };

  if (!prompt) {
    res.status(400).json({ success: false, error: "prompt is required" });
    return;
  }

  const [width, height] = DIMS[size_id] ?? DIMS["9:16"];

  try {
    const token = await freshToken();

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
      res.json({ success: true, queue_id: data.data[0].queue_id, token });
    } else {
      res.status(502).json({ success: false, error: data.msg ?? "Task submission failed", raw: data });
    }
  } catch (err) {
    req.log.error(err);
    res.status(500).json({ success: false, error: String(err) });
  }
});

/**
 * POST /api/clipfly/image-to-image
 * Auto-creates a new account, uploads the image, submits task.
 * Body: { prompt, base64, filename? }
 * Returns: { success, queue_id, token }
 */
router.post("/image-to-image", async (req: Request, res: Response) => {
  const { prompt, base64, filename = "image.jpg" } = req.body as {
    prompt: string;
    base64: string;
    filename?: string;
  };

  if (!prompt || !base64) {
    res.status(400).json({ success: false, error: "prompt and base64 are required" });
    return;
  }

  try {
    const token = await freshToken();
    const { storage_path, material_id } = await uploadImage(base64, filename, token);

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
        source_image: storage_path,
        materialId: material_id,
        model_id: "nanobanana2",
        is_scale: 1,
      },
      { headers: clipflyHeaders(token) },
    );

    if (data.code === 0 && data.data?.[0]?.queue_id) {
      res.json({ success: true, queue_id: data.data[0].queue_id, token });
    } else {
      res.status(502).json({ success: false, error: data.msg ?? "Task submission failed", raw: data });
    }
  } catch (err) {
    req.log.error(err);
    res.status(500).json({ success: false, error: String(err) });
  }
});

/**
 * POST /api/clipfly/image-combination
 * Auto-creates a new account, uploads all images, submits task.
 * Body: { prompt, images: [{ base64, filename }], size_id? }
 * Returns: { success, queue_id, token }
 */
router.post("/image-combination", async (req: Request, res: Response) => {
  const { prompt, images, size_id = "1:1" } = req.body as {
    prompt: string;
    images: Array<{ base64: string; filename?: string }>;
    size_id?: string;
  };

  if (!prompt || !Array.isArray(images) || images.length < 2) {
    res.status(400).json({ success: false, error: "prompt and images[] (at least 2) are required" });
    return;
  }

  const [width, height] = DIMS[size_id] ?? DIMS["1:1"];

  try {
    const token = await freshToken();

    const uploaded = await Promise.all(
      images.map((img, i) => uploadImage(img.base64, img.filename ?? `image_${i}.jpg`, token)),
    );

    const source_images = uploaded.map((u) => u.storage_path);
    const material_ids = uploaded.map((u) => u.material_id);

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
      res.json({ success: true, queue_id: data.data[0].queue_id, token });
    } else {
      res.status(502).json({ success: false, error: data.msg ?? "Task submission failed", raw: data });
    }
  } catch (err) {
    req.log.error(err);
    res.status(500).json({ success: false, error: String(err) });
  }
});

/**
 * POST /api/clipfly/text-to-video
 * Auto-creates a new account each call.
 * Body: { prompt, model?, ratio? }
 * Returns: { success, queue_id, token }
 */
router.post("/text-to-video", async (req: Request, res: Response) => {
  const {
    prompt,
    audio = "",
    model = "wan",
    ratio = "16:9",
  } = req.body as {
    prompt: string;
    audio?: string;
    model?: "seedance" | "wan";
    ratio?: string;
  };

  if (!prompt) {
    res.status(400).json({ success: false, error: "prompt is required" });
    return;
  }

  const model_id = model === "seedance" ? "25" : "29";
  const duration = model === "seedance" ? "5" : "10";

  try {
    const token = await freshToken();

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
      res.json({ success: true, queue_id: data.data.id, token });
    } else {
      res.status(502).json({ success: false, error: data.msg ?? "Task submission failed", raw: data });
    }
  } catch (err) {
    req.log.error(err);
    res.status(500).json({ success: false, error: String(err) });
  }
});

/**
 * POST /api/clipfly/image-to-video
 * Auto-creates a new account, uploads the image, submits task.
 * Body: { prompt, base64, filename?, model? }
 * Returns: { success, queue_id, token }
 */
router.post("/image-to-video", async (req: Request, res: Response) => {
  const {
    prompt,
    base64,
    filename = "image.jpg",
    audio = "",
    model = "wan",
  } = req.body as {
    prompt: string;
    base64: string;
    filename?: string;
    audio?: string;
    model?: "seedance" | "lumen" | "wan";
  };

  if (!prompt || !base64) {
    res.status(400).json({ success: false, error: "prompt and base64 are required" });
    return;
  }

  let model_id: string;
  let material_id_static: string;
  const duration = "10";

  if (model === "seedance") {
    model_id = "25"; material_id_static = "966489002510778368";
  } else if (model === "lumen") {
    model_id = "17"; material_id_static = "969029917515165696";
  } else {
    model_id = "29"; material_id_static = "966341557070827520";
  }

  try {
    const token = await freshToken();
    const { storage_path } = await uploadImage(base64, filename, token);

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
            source_image: storage_path,
            img_style_id: "111",
            materialId: material_id_static,
            is_scale: 0,
            negative_prompt: "",
            from: "image",
            urls: { url: storage_path },
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
      res.json({ success: true, queue_id: data.data.id, token });
    } else {
      res.status(502).json({ success: false, error: data.msg ?? "Task submission failed", raw: data });
    }
  } catch (err) {
    req.log.error(err);
    res.status(500).json({ success: false, error: String(err) });
  }
});

/**
 * GET /api/clipfly/image-status?queue_id=...
 * Requires: Authorization header (token returned from POST)
 */
router.get("/image-status", async (req: Request, res: Response) => {
  const { queue_id } = req.query as { queue_id: string };
  const token = (req.query.token as string) || (req.headers.authorization as string);

  if (!queue_id || !token) {
    res.status(400).json({ success: false, error: "queue_id and token (query or Authorization header) are required" });
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
 * Requires: Authorization header (token returned from POST)
 */
router.get("/video-status", async (req: Request, res: Response) => {
  const { queue_id } = req.query as { queue_id: string };
  const token = (req.query.token as string) || (req.headers.authorization as string);

  if (!queue_id || !token) {
    res.status(400).json({ success: false, error: "queue_id and token (query or Authorization header) are required" });
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
