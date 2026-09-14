import asyncio
import json
from collections.abc import AsyncGenerator

from app.schemas.provider_proxy import Attachment
from app.services.http_client import get_shared_client
from app.services.providers.base import ProviderClient

_SEMAPHORE = asyncio.Semaphore(8)


def _build_anthropic_content(prompt: str, attachments: list[Attachment] | None):
    """Build Anthropic content blocks: text + image (base64) blocks."""
    blocks: list[dict] = [{"type": "text", "text": prompt}]
    if attachments:
        for att in attachments:
            if att.type.startswith("image/"):
                media_type = att.type if "/" in att.type else "image/png"
                blocks.append(
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": att.content,
                        },
                    }
                )
    return blocks


class AnthropicClient(ProviderClient):
    async def list_models(self, endpoint: str, api_key: str) -> list[str]:
        # Anthropic model listing endpoint is not consistently available across gateways.
        # Return an empty list so callers can provide manual model entry fallback.
        return []

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
    ) -> str:
        base = endpoint.rstrip("/") if endpoint else "https://api.anthropic.com"
        url = f"{base}/v1/messages"
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        content = _build_anthropic_content(prompt, attachments)
        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": content}],
        }
        client = get_shared_client(timeout)
        async with _SEMAPHORE:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        content = data.get("content", [])
        if not content:
            return ""
        first = content[0]
        return first.get("text", "")

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
    ) -> AsyncGenerator[str, None]:
        base = endpoint.rstrip("/") if endpoint else "https://api.anthropic.com"
        url = f"{base}/v1/messages"
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
            "accept": "text/event-stream",
        }
        content = _build_anthropic_content(prompt, attachments)
        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": content}],
            "stream": True,
        }
        client = get_shared_client(timeout)
        async with _SEMAPHORE:
            async with client.stream("POST", url, json=payload, headers=headers) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line or line.startswith(":"):
                        continue
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:].strip()
                    if not data_str or data_str == "[DONE]":
                        continue
                    try:
                        data = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue
                    dtype = data.get("type", "")
                    if dtype == "content_block_delta":
                        delta = data.get("delta", {}) or {}
                        if delta.get("type") == "text_delta":
                            text = delta.get("text", "")
                            if text:
                                yield str(text)
                    elif dtype == "message_delta":
                        delta = data.get("delta", {}) or {}
                        text = delta.get("text", "")
                        if text:
                            yield str(text)
