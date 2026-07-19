import json
from collections.abc import AsyncGenerator

import httpx
from fastapi import HTTPException, status

from app.schemas.provider_proxy import Attachment
from app.services.providers.base import ProviderClient


def _build_openai_content(prompt: str, attachments: list[Attachment] | None):
    """Build the user message content.

    Returns either a plain string (text only) or a multimodal content array
    with text + image_url blocks when image attachments are present.
    """
    image_parts = []
    if attachments:
        for att in attachments:
            if att.type.startswith("image/"):
                image_parts.append(
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{att.type};base64,{att.content}"
                        },
                    }
                )
    if not image_parts:
        return prompt
    content: list[dict] = [{"type": "text", "text": prompt}]
    content.extend(image_parts)
    return content


class OpenAICompatibleClient(ProviderClient):
    USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    async def list_models(self, endpoint: str, api_key: str) -> list[str]:
        base = endpoint.rstrip("/") if endpoint else "https://api.openai.com/v1"
        url = f"{base}/models"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json", "User-Agent": self.USER_AGENT}
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                resp = await client.get(url, headers=headers)
                # Some providers (e.g. Perplexity) don't use /v1 in base_url but need it for /models — retry with /v1 on 404
                if resp.status_code == 404 and "/v1" not in base:
                    alt_url = f"{base.rstrip('/')}/v1/models"
                    resp = await client.get(alt_url, headers=headers)
                # Some providers (e.g. Ollama on a custom port) add /v1 but the models endpoint is at root — retry without /v1 on 404
                if resp.status_code == 404 and "/v1" in base:
                    alt_base = base.replace("/v1", "")
                    alt_url = f"{alt_base}/models"
                    resp = await client.get(alt_url, headers=headers)
                resp.raise_for_status()
                data = resp.json()

                rows = data.get("data", [])
                models: list[str] = []
                for row in rows:
                    model_id = row.get("id")
                    if isinstance(model_id, str) and model_id:
                        models.append(model_id)
                return sorted(models)
            except httpx.HTTPStatusError as e:
                # Return empty list gracefully for providers that don't support model listing
                # or return rate limiting / auth errors during model discovery
                if e.response.status_code in [401, 404, 405, 429, 502]:
                    return []
                raise

    async def chat(
        self,
        endpoint: str,
        api_key: str,
        model: str,
        prompt: str,
        max_tokens: int,
        temperature: float,
        attachments: list[Attachment] | None = None,
    ) -> str:
        base = endpoint.rstrip("/") if endpoint else "https://api.openai.com/v1"
        url = f"{base}/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json", "User-Agent": self.USER_AGENT}
        content = _build_openai_content(prompt, attachments)
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": content}],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        async with httpx.AsyncClient(timeout=120) as client:
            try:
                resp = await client.post(url, json=payload, headers=headers)
                # Some providers (e.g. Perplexity) don't use /v1 — retry without it on 404
                if resp.status_code == 404 and "/v1" in base:
                    alt_base = base.replace("/v1", "")
                    alt_url = f"{alt_base}/chat/completions"
                    resp = await client.post(alt_url, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()

                choices = data.get("choices", [])
                if not choices:
                    return ""
                message = choices[0].get("message", {})
                return message.get("content", "") or ""
            except httpx.HTTPStatusError as e:
                # Handle specific error cases for better error messages
                if e.response.status_code == status.HTTP_401_UNAUTHORIZED:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail=f"Authentication failed (401): Invalid API key for {base}"
                    ) from e
                if e.response.status_code == status.HTTP_404_NOT_FOUND:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Endpoint not found (404): {url}"
                    ) from e
                if e.response.status_code == status.HTTP_502_BAD_GATEWAY:
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail=f"Bad Gateway (502): Could not reach the provider at {base}"
                    ) from e
                if e.response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail=f"Rate limited (429): Too many requests to {base}"
                    ) from e
                raise

    async def chat_stream(
        self,
        endpoint: str,
        api_key: str,
        model: str,
        prompt: str,
        max_tokens: int,
        temperature: float,
        attachments: list[Attachment] | None = None,
    ) -> AsyncGenerator[str, None]:
        base = endpoint.rstrip("/") if endpoint else "https://api.openai.com/v1"
        url = f"{base}/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json", "User-Agent": self.USER_AGENT}
        content = _build_openai_content(prompt, attachments)
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": content}],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
        }
        async with httpx.AsyncClient(timeout=120) as client:
            try:
                async with client.stream("POST", url, json=payload, headers=headers) as resp:
                    if resp.status_code == 404 and "/v1" in base:
                        alt_base = base.replace("/v1", "")
                        alt_url = f"{alt_base}/chat/completions"
                        async with client.stream("POST", alt_url, json=payload, headers=headers) as resp2:
                            resp2.raise_for_status()
                            async for line in resp2.aiter_lines():
                                if not line or line.startswith(":"):
                                    continue
                                if line.startswith("data: "):
                                    data_str = line[6:]
                                    if data_str.strip() == "[DONE]":
                                        return
                                    try:
                                        data = json.loads(data_str)
                                        choices = data.get("choices", [])
                                        if choices:
                                            delta = choices[0].get("delta", {})
                                            content = delta.get("content", "")
                                            if content:
                                                yield content
                                    except json.JSONDecodeError:
                                        continue
                        return
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if not line or line.startswith(":"):
                            continue
                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str.strip() == "[DONE]":
                                return
                            try:
                                data = json.loads(data_str)
                                choices = data.get("choices", [])
                                if choices:
                                    delta = choices[0].get("delta", {})
                                    content = delta.get("content", "")
                                    if content:
                                        yield content
                            except json.JSONDecodeError:
                                continue
            except httpx.HTTPStatusError as e:
                if e.response.status_code == status.HTTP_401_UNAUTHORIZED:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail=f"Authentication failed (401): Invalid API key for {base}"
                    ) from e
                if e.response.status_code == status.HTTP_404_NOT_FOUND:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Endpoint not found (404): {url}"
                    ) from e
                if e.response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail=f"Rate limited (429): Too many requests to {base}"
                    ) from e
                raise
