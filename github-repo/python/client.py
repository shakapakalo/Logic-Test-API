"""
AI API Python Client
====================
A simple, reusable client for the AI API server.
Supports Clipfly (image & video) and GeminiGen (video) generation.

Usage:
    from client import AIClient

    client = AIClient("http://YOUR_VPS_IP:3000/api")

    # Generate image from text
    result = client.clipfly_text_to_image("A sunset over the ocean", size="16:9")
    print(result["url"])

    # Generate video from text
    result = client.geminigen_video("A futuristic city at night", model="veo_fast")
    print(result["video_url"])
"""

import requests
import base64
import time
from pathlib import Path


class AIClient:
    def __init__(self, base_url: str = "http://localhost:3000/api", timeout: int = 90, poll_interval: int = 5, max_polls: int = 72):
        """
        Args:
            base_url     : Full API base URL e.g. http://1.2.3.4:3000/api
            timeout      : Request timeout in seconds
            poll_interval: Seconds between status polls
            max_polls    : Maximum poll attempts before giving up (~6 min)
        """
        self.base = base_url.rstrip("/")
        self.timeout = timeout
        self.poll_interval = poll_interval
        self.max_polls = max_polls

    # ─── Helpers ──────────────────────────────────────────────────────────────

    def _post(self, path: str, json: dict) -> dict:
        r = requests.post(f"{self.base}{path}", json=json, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def _get(self, path: str, params: dict = None, headers: dict = None) -> dict:
        r = requests.get(f"{self.base}{path}", params=params, headers=headers, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    @staticmethod
    def load_image(path: str) -> str:
        """Load an image file and return as base64 string."""
        return base64.b64encode(Path(path).read_bytes()).decode()

    def _poll_image(self, queue_id, token) -> dict:
        """Poll until image task completes. Returns final dict."""
        for i in range(self.max_polls):
            d = self._get("/clipfly/image-status", params={"queue_id": queue_id}, headers={"Authorization": token})
            s = d.get("status")
            print(f"  [{i+1:02d}] image status: {s}")
            if s == "completed":
                return d
            if s == "failed":
                raise RuntimeError(f"Image task failed: {d.get('reason')}")
            time.sleep(self.poll_interval)
        raise TimeoutError("Image task timed out")

    def _poll_video_clipfly(self, queue_id, token) -> dict:
        """Poll until Clipfly video task completes. Returns final dict."""
        for i in range(self.max_polls):
            d = self._get("/clipfly/video-status", params={"queue_id": queue_id}, headers={"Authorization": token})
            s = d.get("status")
            print(f"  [{i+1:02d}] video status: {s}")
            if s == "completed":
                return d
            if s == "failed":
                raise RuntimeError(f"Video task failed: {d.get('reason')}")
            time.sleep(self.poll_interval)
        raise TimeoutError("Video task timed out")

    def _poll_geminigen(self, uuid, access_token) -> dict:
        """Poll until GeminiGen video task completes. Returns final dict."""
        for i in range(self.max_polls):
            d = self._get(f"/geminigen/status/{uuid}", params={"access_token": access_token})
            s = d.get("status")
            print(f"  [{i+1:02d}] geminigen status: {s}")
            if s == "completed":
                return d
            if s == "failed":
                raise RuntimeError(f"GeminiGen task failed: {d.get('reason')}")
            time.sleep(self.poll_interval)
        raise TimeoutError("GeminiGen task timed out")

    # ─── Clipfly Methods ──────────────────────────────────────────────────────

    def clipfly_text_to_image(self, prompt: str, size: str = "16:9") -> dict:
        """
        Generate an image from a text prompt.

        Args:
            prompt: Text description of the image
            size  : Aspect ratio — "1:1", "9:16", "16:9", "3:4", "4:3", "2:3", "3:2", "21:9"

        Returns:
            { "status": "completed", "url": "https://..." }
        """
        print(f"[Clipfly] Submitting text-to-image task...")
        resp = self._post("/clipfly/text-to-image", {"prompt": prompt, "size_id": size})
        if not resp.get("success"):
            raise RuntimeError(f"Submission failed: {resp}")
        print(f"  queue_id={resp['queue_id']} (fresh account auto-created)")
        return self._poll_image(resp["queue_id"], resp["token"])

    def clipfly_image_to_image(self, prompt: str, image_path: str) -> dict:
        """
        Transform an existing image using a prompt.

        Args:
            prompt    : Transformation description
            image_path: Path to input image file (JPEG/PNG)

        Returns:
            { "status": "completed", "url": "https://..." }
        """
        print(f"[Clipfly] Submitting image-to-image task...")
        b64 = self.load_image(image_path)
        resp = self._post("/clipfly/image-to-image", {
            "prompt": prompt, "base64": b64, "filename": Path(image_path).name
        })
        if not resp.get("success"):
            raise RuntimeError(f"Submission failed: {resp}")
        print(f"  queue_id={resp['queue_id']}")
        return self._poll_image(resp["queue_id"], resp["token"])

    def clipfly_image_combination(self, prompt: str, image_paths: list, size: str = "1:1") -> dict:
        """
        Combine multiple images into one.

        Args:
            prompt     : How to combine the images
            image_paths: List of image file paths (minimum 2)
            size       : Output aspect ratio

        Returns:
            { "status": "completed", "url": "https://..." }
        """
        if len(image_paths) < 2:
            raise ValueError("At least 2 images required")
        print(f"[Clipfly] Submitting image-combination task ({len(image_paths)} images)...")
        images = [{"base64": self.load_image(p), "filename": Path(p).name} for p in image_paths]
        resp = self._post("/clipfly/image-combination", {"prompt": prompt, "images": images, "size_id": size})
        if not resp.get("success"):
            raise RuntimeError(f"Submission failed: {resp}")
        print(f"  queue_id={resp['queue_id']}")
        return self._poll_image(resp["queue_id"], resp["token"])

    def clipfly_text_to_video(self, prompt: str, model: str = "wan", ratio: str = "16:9") -> dict:
        """
        Generate a video from a text prompt.

        Args:
            prompt: Text description of the video
            model : "wan" (10s) or "seedance" (5s)
            ratio : "16:9", "9:16", "1:1"

        Returns:
            { "status": "completed", "url": "https://..." }
        """
        print(f"[Clipfly] Submitting text-to-video task (model={model})...")
        resp = self._post("/clipfly/text-to-video", {"prompt": prompt, "model": model, "ratio": ratio})
        if not resp.get("success"):
            raise RuntimeError(f"Submission failed: {resp}")
        print(f"  queue_id={resp['queue_id']}")
        return self._poll_video_clipfly(resp["queue_id"], resp["token"])

    def clipfly_image_to_video(self, prompt: str, image_path: str, model: str = "wan") -> dict:
        """
        Animate an image into a video.

        Args:
            prompt    : Motion/animation description
            image_path: Path to input image file
            model     : "wan", "seedance", or "lumen"

        Returns:
            { "status": "completed", "url": "https://..." }
        """
        print(f"[Clipfly] Submitting image-to-video task (model={model})...")
        b64 = self.load_image(image_path)
        resp = self._post("/clipfly/image-to-video", {
            "prompt": prompt, "base64": b64, "filename": Path(image_path).name, "model": model
        })
        if not resp.get("success"):
            raise RuntimeError(f"Submission failed: {resp}")
        print(f"  queue_id={resp['queue_id']}")
        return self._poll_video_clipfly(resp["queue_id"], resp["token"])

    # ─── GeminiGen Methods ────────────────────────────────────────────────────

    def geminigen_text_to_video(self, prompt: str, model: str = "veo_fast", aspect_ratio: str = "16:9") -> dict:
        """
        Generate a video from text using GeminiGen (Veo or Grok).

        Args:
            prompt      : Text description of the video
            model       : "veo_fast", "veo_lite", or "grok"
            aspect_ratio: "16:9", "9:16", or "1:1"

        Returns:
            { "status": "completed", "video_url": "https://..." }
        """
        print(f"[GeminiGen] Submitting text-to-video (model={model})...")
        resp = self._post("/geminigen/video-gen", {"prompt": prompt, "model": model, "aspect_ratio": aspect_ratio})
        if not resp.get("success"):
            raise RuntimeError(f"Submission failed: {resp}")
        print(f"  uuid={resp['uuid']}")
        return self._poll_geminigen(resp["uuid"], resp["access_token"])

    def geminigen_image_to_video(self, prompt: str, image_paths: list, model: str = "veo_fast", aspect_ratio: str = "16:9") -> dict:
        """
        Generate a video from one or more images using GeminiGen.

        Args:
            prompt      : Motion/animation description
            image_paths : List of image file paths (1 image for veo, up to 3 for grok)
            model       : "veo_fast", "veo_lite", or "grok"
            aspect_ratio: "16:9", "9:16", or "1:1"

        Returns:
            { "status": "completed", "video_url": "https://..." }
        """
        print(f"[GeminiGen] Submitting image-to-video (model={model}, {len(image_paths)} image(s))...")
        images = [{"base64": self.load_image(p), "filename": Path(p).name} for p in image_paths]
        resp = self._post("/geminigen/video-gen", {
            "prompt": prompt, "model": model, "aspect_ratio": aspect_ratio, "images": images
        })
        if not resp.get("success"):
            raise RuntimeError(f"Submission failed: {resp}")
        print(f"  uuid={resp['uuid']}")
        return self._poll_geminigen(resp["uuid"], resp["access_token"])

    def health(self) -> bool:
        """Check if the API server is running."""
        try:
            d = self._get("/healthz")
            return d.get("status") == "ok"
        except Exception:
            return False
