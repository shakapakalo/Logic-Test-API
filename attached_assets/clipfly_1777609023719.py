import requests
import random
import string
import time
import io
import mimetypes
import base64
import asyncio
from fake_useragent import UserAgent
from PIL import Image

ua = UserAgent()

def generate_random_ip(): 
    return ".".join(map(str, (random.randint(1, 254) for _ in range(4))))

def get_headers(token=None):
    random_ip = generate_random_ip()
    headers = {
        "User-Agent": ua.random,
        "accept": "application/json, text/plain, */*",
        "content-type": "application/json",
        "x-app-id": "app-fotor-web",
        "origin": "https://www.clipfly.ai",
        "referer": "https://www.clipfly.ai/",
        "X-Forwarded-For": random_ip,
        "X-Real-IP": random_ip,
        "Client-IP": random_ip,
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-site": "same-origin",
        "sec-fetch-mode": "cors",
        "sec-fetch-dest": "empty"
    }
    if token: headers["authorization"] = token
    return headers

def compress_image_sync(file_bytes, original_filename, max_mb=4.8):
    max_bytes = int(max_mb * 1024 * 1024)
    if len(file_bytes) <= max_bytes: return file_bytes, original_filename
    try:
        img = Image.open(io.BytesIO(file_bytes))
        if img.mode in ("RGBA", "P"): img = img.convert("RGB")
        
        max_dimension = 3840 
        if max(img.width, img.height) > max_dimension:
            ratio = max_dimension / max(img.width, img.height)
            img = img.resize((int(img.width * ratio), int(img.height * ratio)), Image.Resampling.LANCZOS)
            
        out = io.BytesIO()
        quality = 85
        scale = 1.0
        
        while True:
            out.seek(0)
            out.truncate()
            temp_img = img.resize((int(img.width * scale), int(img.height * scale)), Image.Resampling.LANCZOS) if scale < 1.0 else img
            temp_img.save(out, format="JPEG", optimize=True, quality=quality)
            if out.tell() <= max_bytes: break
            if quality > 30: quality -= 15  
            else: scale *= 0.75; quality = 70   
            
        filename_without_ext = original_filename.rsplit('.', 1)[0] if '.' in original_filename else original_filename
        new_filename = f"{filename_without_ext}_compressed.jpg"
        return out.getvalue(), new_filename
    except Exception as e:
        print(f"Compress Error: {e}")
        return file_bytes, original_filename

def register_clipfly_sync():
    url = "https://www.clipfly.ai/api/v1/account/register"
    for attempt in range(10): 
        try:
            username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
            email = f"{username}@znsj.com"
            password = "User" + ''.join(random.choices(string.ascii_lowercase, k=8)) + "!"
            payload = {"email": email, "password": password, "ref": None, "activity_id": None, "invitor_id": None}
            
            r = requests.post(url, json=payload, headers=get_headers(), timeout=15).json()
            if r.get("code") == 0: return r["data"]["token"]["token"], None
        except requests.exceptions.RequestException:
            time.sleep(2)
        except Exception as e:
            return None, f"Error sistem: {e}"
    return None, "Gagal register ke Clipfly setelah 10x percobaan."

def upload_to_clipfly_sync(b64, name, token):
    url = "https://www.clipfly.ai/api/v1/common/upload/base64"
    mime_type, _ = mimetypes.guess_type(name)
    payload = {
        "content": f"data:{mime_type or 'image/jpeg'};base64,{b64}",
        "name": name, "file_type": "image", "is_original_name": 0, "prefix_path": "/uploads"
    }
    for attempt in range(10): 
        try:
            res = requests.post(url, json=payload, headers=get_headers(token), timeout=30).json()
            if res.get("code") == 0:
                return res["data"]["storage_path"], str(res["data"].get("user_id") or res["data"]["storage_path"].split('/')[3]), None
        except requests.exceptions.RequestException:
            time.sleep(2)
        except Exception as e:
            return None, None, f"Error sistem: {e}"
    return None, None, "Timeout saat unggah gambar (gagal 10x)."

def submit_text_to_image_task_sync(p, t, s_id):
    url = "https://www.clipfly.ai/api/v1/user/ai-tasks/image-generator/create"
    dims = {"1:1": (2048, 2048), "9:16": (1536, 2752), "16:9": (2752, 1536), "3:4": (1536, 2048), "4:3": (2048, 1536), "2:3": (1536, 2304), "3:2": (2304, 1536), "21:9": (3264, 1408)}
    width, height = dims.get(s_id, (1536, 2752))
    payload = {"type": 21, "prompt": p, "negative_prompt": "", "gnum": 1, "style_id": "", "size_id": s_id, "model_id": "nanobanana2", "height": height, "width": width, "is_scale": 1}
    for _ in range(10): 
        try:
            r = requests.post(url, json=payload, headers=get_headers(t), timeout=30).json()
            if r.get("code") == 0: return r["data"][0]["queue_id"], None
        except requests.exceptions.RequestException:
            time.sleep(2)
        except Exception as e:
            return None, str(e)
    return None, "Gagal terhubung Clipfly T2I (10x)."

def submit_image_task_sync(p_th, p, t, m_id):
    url = "https://www.clipfly.ai/api/v1/user/ai-tasks/image-generator/create"
    payload = {"type": 22, "prompt": p, "gnum": 1, "source_image": p_th, "materialId": m_id, "model_id": "nanobanana2", "is_scale": 1}
    for _ in range(10): 
        try:
            r = requests.post(url, json=payload, headers=get_headers(t), timeout=30).json()
            if r.get("code") == 0: return r["data"][0]["queue_id"], None
        except requests.exceptions.RequestException:
            time.sleep(2)
        except Exception as e:
            return None, str(e)
    return None, "Koneksi terputus Clipfly I2I (10x)."

def submit_image_combination_task_sync(p_ths, p, t, m_ids, s_id):
    url = "https://www.clipfly.ai/api/v1/user/ai-tasks/image-generator/create"
    dims = {"1:1": (2048, 2048), "9:16": (1536, 2752), "16:9": (2752, 1536), "3:4": (1536, 2048), "4:3": (2048, 1536), "2:3": (1536, 2304), "3:2": (2304, 1536), "21:9": (3264, 1408)}
    width, height = dims.get(s_id, (1536, 2752))
    payload = {
        "type": 47, "prompt": p, "negative_prompt": "", "gnum": 1, "size_id": s_id, 
        "source_image": p_ths, "materialId": m_ids, "model_id": "nanobanana2", 
        "is_scale": 1, "width": width, "height": height
    }
    for _ in range(10): 
        try:
            r = requests.post(url, json=payload, headers=get_headers(t), timeout=30).json()
            if r.get("code") == 0: return r["data"][0]["queue_id"], None
        except requests.exceptions.RequestException:
            time.sleep(2)
        except Exception as e:
            return None, str(e)
    return None, "Koneksi terputus API Image Combination (10x)."

def submit_text_to_video_task_sync(p, t, aud, m, r):
    url = "https://www.clipfly.ai/api/v1/user/ai-task-queues"
    if m == "seedance":
        model_id = "25"; duration = "5"
    else: 
        model_id = "29"; duration = "10"
    payload = {
        "type": 16, 
        "attrs": [{
            "camera_control": "auto", "is_scale": 0, "prompt": p, 
            "enhance": True, "style": "general", "negative_prompt": "", 
            "ratio": r, "from": "text", "voice": aud, 
            "model_id": model_id, "camerafixed": False, "duration": duration, 
            "audio_type": 0, "biz_type": 16
        }]
    }
    for _ in range(10): 
        try:
            res = requests.post(url, json=payload, headers=get_headers(t), timeout=30).json()
            if res.get("code") == 0: return res["data"]["id"], None
        except requests.exceptions.RequestException:
            time.sleep(2)
        except Exception as e:
            return None, str(e)
    return None, "Gagal terhubung Server AI Video (10x)."

def submit_video_task_sync(path, p, t, aud, m):
    url = "https://www.clipfly.ai/api/v1/user/ai-task-queues"
    if m == "seedance":
        model_id = "25"; material_id = "966489002510778368"; duration = "10"
    elif m == "lumen":
        model_id = "17"; material_id = "969029917515165696"; duration = "10"
    else: 
        model_id = "29"; material_id = "966341557070827520"; duration = "10"
    payload = {
        "type": 17, 
        "attrs": [{
            "maskImage": "", "prompt": p, "camera_control": "auto", 
            "source_image": path, "img_style_id": "111", 
            "materialId": material_id, "is_scale": 0, "negative_prompt": "", 
            "from": "image", "urls": { "url": path }, "voice": aud, 
            "model_id": model_id, "camerafixed": False, "duration": duration, 
            "audio_type": 0, "biz_type": 17
        }]
    }
    for _ in range(10): 
        try:
            r = requests.post(url, json=payload, headers=get_headers(t), timeout=30)
            res = r.json()
            if res.get("code") == 0: return res["data"]["id"], None
            api_msg = res.get("msg", "") or res.get("message", "Gagal memproses.")
            return None, f"Ditolak Server API: {api_msg}"
        except requests.exceptions.RequestException:
            time.sleep(2)
        except Exception as e:
            return None, f"Error sistem: {str(e)}"
    return None, "Server Request berulang (10x)."

def check_task_api_sync(url, token):
    return requests.get(url, headers=get_headers(token), timeout=15).json()

async def poll_clipfly_task(q_id, t, is_img=True):
    url = f"https://www.clipfly.ai/api/v1/user/ai-tasks/{'image-generator/queue-detail' if is_img else 'list'}?queue_id={q_id}"
    for _ in range(60): 
        await asyncio.sleep(5)
        try:
            res = await asyncio.to_thread(check_task_api_sync, url, t)
            if res.get("code") == 0 and res.get("data"):
                info = res["data"][0]
                if is_img:
                    if info.get("after_material"): return "success", "https://www.clipfly.ai" + info["after_material"]["urls"]["url"]
                    elif info.get("status") == 3: return "failed", info.get("fail_reason")
                else:
                    if info["status"] == 2: return "success", "https://www.clipfly.ai" + info["ext"]["output_path"]
                    elif info["status"] == 3: return "failed", info.get("fail_reason")
        except Exception as e: 
            pass
    return "timeout", None
