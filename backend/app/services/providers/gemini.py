import asyncio
import json
from collections.abc import AsyncGenerator

import httpx

from app.schemas.provider_proxy import Attachment
from app.services.http_client import get_shared_client
from app.services.providers.base import ProviderClient

_SEMAPHORE = asyncio.Semaphore(8)


def _build_gemini_parts(prompt: str, attachments: list[Attachment] | None) -> list[dict]:
    parts: list[dict] = [{"text": prompt}]
    if attachments:
        for att in attachments:
            if att.type.startswith("image/"):
                parts.append(
                    {
                        "inline_data": {
                            "mime_type": att.type,
                            "data": att.content,
                        }
                    }
                )
    return parts


def _extract_gemini_text(data: dict) -> str:
    """Extract concatenated text from a Gemini generateContent payload."""
    texts: list[str] = []
    for cand in data.get("candidates", []) or []:
        content = cand.get("content", {}) or {}
        for part in content.get("parts", []) or []:
            t = part.get("text")
            if isinstance(t, str) and t:
                texts.append(t)
    return "".join(texts)


class GeminiClient(ProviderClient):
    def _urls(self, base: str, model: str, api_key: str, oauth_token: str = "") -> tuple[str, dict]:
        if oauth_token:
            url = f"{base}/v1beta/models/{model}:generateContent"
            headers = {
                "Authorization": f"Bearer {oauth_token}",
                "Content-Type": "application/json",
            }
        else:
            url = f"{base}/v1beta/models/{model}:generateContent?key={api_key}"
            headers = {"Content-Type": "application/json"}
        return url, headers

    def _stream_urls(self, base: str, model: str, api_key: str, oauth_token: str = "") -> tuple[str, dict]:
        if oauth_token:
            url = f"{base}/v1beta/models/{model}:streamGenerateContent?alt=sse"
            headers = {
                "Authorization": f"Bearer {oauth_token}",
                "Content-Type": "application/json",
            }
        else:
            url = f"{base}/v1beta/models/{model}:streamGenerateContent?alt=sse&key={api_key}"
            headers = {"Content-Type": "application/json"}
        return url, headers

    async def list_models(self, endpoint: str, api_key: str, oauth_token: str = "") -> list[str]:
        base = endpoint.rstrip("/") if endpoint else "https://generativelanguage.googleapis.com"
        headers: dict[str, str] = {}
        if oauth_token:
            url = f"{base}/v1beta/models"
            headers = {"Authorization": f"Bearer {oauth_token}"}
        else:
            url = f"{base}/v1beta/models?key={api_key}"
        client = get_shared_client(30)
        resp = await client.get(url, headers=headers or None)
        resp.raise_for_status()
        data = resp.json()

        rows = data.get("models", [])
        out: list[str] = []
        for row in rows:
            name = row.get("name", "")
            if isinstance(name, str) and name:
                out.append(name.split("/")[-1])
        return sorted(out)

    async def chat(
        self,
        endpoint: str,
        api_key: str,
        model: str,
        prompt: str,
        max_tokens: int,
        temperature: float,
        attachments: list[Attachment] | None = None,
        timeout: int = 120,
        oauth_token: str = "",
    ) -> str:
        base = endpoint.rstrip("/") if endpoint else "https://generativelanguage.googleapis.com"
        url, headers = self._urls(base, model, api_key, oauth_token)
        parts = _build_gemini_parts(prompt, attachments)
        payload = {
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
            "contents": [{"parts": parts}],
        }
        client = get_shared_client(timeout)
        async with _SEMAPHORE:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        candidates = data.get("candidates", [])
        if not candidates:
            return ""
        parts = candidates[0].get("content", {}).get("parts", [])
        if not parts:
            return ""
        return parts[0].get("text", "")

    async def chat_stream(
        self,
        endpoint: str,
        api_key: str,
        model: str,
        prompt: str,
        max_tokens: int,
        temperature: float,
        attachments: list[Attachment] | None = None,
        timeout: int = 120,
        oauth_token: str = "",
    ) -> AsyncGenerator[str, None]:
        base = endpoint.rstrip("/") if endpoint else "https://generativelanguage.googleapis.com"
        url, headers = self._stream_urls(base, model, api_key, oauth_token)
        parts = _build_gemini_parts(prompt, attachments)
        payload = {
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
            "contents": [{"parts": parts}],
        }
        client = get_shared_client(timeout)
        async with _SEMAPHORE:
            async with client.stream("POST", url, json=payload, headers=headers) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line or line.startswith(":"):
                        continue
                    if line.startswith("data: "):
                        data_str = line[6:].strip()
                        if not data_str or data_str == "[DONE]":
                            continue
                        try:
                            data = json.loads(data_str)
                        except json.JSONDecodeError:
                            continue
                        text = _extract_gemini_text(data)
                        if text:
                            yield text
