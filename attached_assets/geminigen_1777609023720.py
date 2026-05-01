import requests
import time
import uuid
import json
import asyncio
import random
import string

def generate_device_token():
    """Menghasilkan device token acak dengan format menyerupai FCM token."""
    chars = string.ascii_letters + string.digits + "-_"
    part1 = ''.join(random.choices(chars, k=22))
    part2 = ''.join(random.choices(chars, k=140))
    return f"{part1}:{part2}"

def get_video_token_sync():
    url = "https://api.geminigen.ai/mobile/v1/uuid/activate-account"
    for attempt in range(10): 
        try:
            current_timestamp = str(int(time.time()))
            headers = {
                "user-agent": "Dart/3.10 (dart:io)",
                "accept": "application/json",
                "accept-encoding": "gzip",
                "x-timestamp": current_timestamp,
                "host": "api.geminigen.ai",
                "content-type": "application/json",
                "x-token": "7822db02280a28d61d6a75d199af010e"
            }
            payload = {
                "mobile_device_uuid": uuid.uuid4().hex[:16],
                "platform": "GenV-APP",
                "device_token": generate_device_token(), # <-- Menggunakan device token acak
                "device_type": "android"
            }
            response = requests.post(url, headers=headers, json=payload, timeout=15)
            response.raise_for_status() 
            return response.json().get("access_token")
        except requests.exceptions.RequestException as e:
            time.sleep(2)
        except Exception as e:
            return None
    return None

def get_geminigen_task_sync(p, t, images, m, r, veo_mode=None):
    # images adalah list of dictionaries: [{'bytes': ..., 'name': ...}, ...]
    for attempt in range(10): 
        try:
            headers = {
                "user-agent": "Dart/3.10 (dart:io)",
                "accept": "application/json",
                "accept-encoding": "gzip",
                "host": "api.geminigen.ai",
                "authorization": f"Bearer {t}"
            }

            if m in ["veo_fast", "veo_lite"]:
                model_payload = "veo-3.1-fast" if m == "veo_fast" else "veo-3.1-lite"
                url = "https://api.geminigen.ai/mobile/v3/video-gen"
                data_payload = {
                    "prompt": p,
                    "model": model_payload,
                    "duration": "8",
                    "resolution": "720p",
                    "aspect_ratio": r,
                    "service_mode": "stable"
                }
                
                # Payload Array untuk Veo (Bisa 1 atau 2 Foto, menggunakan key 'image' yang diulang)
                files_payload = [
                    ("image", (img['name'], img['bytes'], "image/jpeg")) for img in images
                ]
                    
                response = requests.post(url, headers=headers, data=data_payload, files=files_payload, timeout=30)
                response.raise_for_status()
                return response.json().get('uuid'), None

            elif m == "grok":
                url = "https://api.geminigen.ai/mobile/v3/video-gen/grok-stream"
                data_payload = {
                    "mode": "custom",
                    "prompt": p,
                    "model": "grok-video",
                    "resolution": "720p",
                    "aspect_ratio": r,
                    "duration": "10",
                    "turnstile_token": "string",
                    "service_mode": "stable"
                }
                
                # Payload Array untuk Multi Foto Grok (Bisa 1, 2, atau 3 Foto, menggunakan key 'files' yang diulang)
                files_payload = [
                    ("files", (img['name'], img['bytes'], "image/jpeg")) for img in images
                ]
                
                response = requests.post(url, headers=headers, data=data_payload, files=files_payload, stream=True, timeout=30)
                response.raise_for_status()
                
                for line in response.iter_lines():
                    if line:
                        decoded_line = line.decode('utf-8')
                        if decoded_line.startswith("data: "):
                            decoded_line = decoded_line[6:]
                        try:
                            json_data = json.loads(decoded_line)
                            history_uuid = json_data.get("history_uuid")
                            if history_uuid:
                                return history_uuid, None
                        except json.JSONDecodeError:
                            continue
                raise requests.exceptions.ConnectionError("Stream terputus")
        except requests.exceptions.RequestException as e:
            time.sleep(3)
        except Exception as e:
            return None, str(e)
            
    return None, "Gagal terhubung API setelah 10x percobaan."

def geminigen_check_status_sync(access_token, video_uuid):
    url = f"https://api.geminigen.ai/mobile/v1/history/{video_uuid}"
    headers = {
        "user-agent": "Dart/3.10 (dart:io)",
        "accept": "application/json",
        "accept-encoding": "gzip",
        "authorization": f"Bearer {access_token}",
        "host": "api.geminigen.ai"
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        return response.json()
    except:
        return None

async def poll_geminigen_task(uuid, t):
    for _ in range(60): 
        await asyncio.sleep(10)
        data = await asyncio.to_thread(geminigen_check_status_sync, t, uuid)
        if data:
            status = data.get("status")
            if status == 2:
                vids = data.get("generated_video", [])
                if vids and len(vids) > 0:
                    return "success", vids[0].get("video_url")
            elif status in [3, 4, -1]: 
                return "failed", data.get("error_message")
    return "timeout", None
