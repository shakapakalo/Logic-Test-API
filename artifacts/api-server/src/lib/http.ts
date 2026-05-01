import axios, { type AxiosRequestConfig } from "axios";

const CLIPFLY_BASE = "https://www.clipfly.ai";
const GEMINIGEN_BASE = "https://api.geminigen.ai";

function randomIp(): string {
  return [1, 2, 3, 4].map(() => Math.floor(Math.random() * 254) + 1).join(".");
}

export function clipflyHeaders(token?: string): Record<string, string> {
  const ip = randomIp();
  const headers: Record<string, string> = {
    "User-Agent":
      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
    accept: "application/json, text/plain, */*",
    "content-type": "application/json",
    "x-app-id": "app-fotor-web",
    origin: CLIPFLY_BASE,
    referer: `${CLIPFLY_BASE}/`,
    "X-Forwarded-For": ip,
    "X-Real-IP": ip,
    "Client-IP": ip,
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-site": "same-origin",
    "sec-fetch-mode": "cors",
    "sec-fetch-dest": "empty",
  };
  if (token) headers["authorization"] = token;
  return headers;
}

export function geminiHeaders(token?: string): Record<string, string> {
  const h: Record<string, string> = {
    "user-agent": "Dart/3.10 (dart:io)",
    accept: "application/json",
    "accept-encoding": "gzip",
    host: "api.geminigen.ai",
  };
  if (token) h["authorization"] = `Bearer ${token}`;
  return h;
}

export async function retryPost<T>(
  url: string,
  data: unknown,
  config: AxiosRequestConfig,
  retries = 10,
  delayMs = 2000,
): Promise<T> {
  let lastErr: unknown;
  for (let i = 0; i < retries; i++) {
    try {
      const res = await axios.post<T>(url, data, {
        ...config,
        timeout: 30000,
        validateStatus: () => true,
      });
      return res.data;
    } catch (err) {
      lastErr = err;
      await new Promise((r) => setTimeout(r, delayMs));
    }
  }
  throw lastErr;
}

export async function retryGet<T>(
  url: string,
  config: AxiosRequestConfig,
  retries = 10,
  delayMs = 2000,
): Promise<T> {
  let lastErr: unknown;
  for (let i = 0; i < retries; i++) {
    try {
      const res = await axios.get<T>(url, {
        ...config,
        timeout: 15000,
        validateStatus: () => true,
      });
      return res.data;
    } catch (err) {
      lastErr = err;
      await new Promise((r) => setTimeout(r, delayMs));
    }
  }
  throw lastErr;
}

export { CLIPFLY_BASE, GEMINIGEN_BASE };
