"""Codex subscription client (ChatGPT subscription-backed Codex API).

Provider key: `codex`
Default base: https://chatgpt.com/backend-api/codex

Auth: the stored api_key is used as the ChatGPT access token
(`Authorization: Bearer <token>`). Optional per-call `account_id` is sent as
`ChatGPT-Account-Id` when provided.
"""

import asyncio
import json
from collections.abc import AsyncGenerator
from typing import Any

import httpx
from fastapi import HTTPException, status

from app.schemas.provider_proxy import Attachment
from app.services.http_client import get_shared_client
from app.services.providers.base import ProviderClient

_SEMAPHORE = asyncio.Semaphore(8)

DEFAULT_BASE = "https://chatgpt.com/backend-api/codex"

CODEX_MODELS: list[str] = [
    "gpt-5.6-sol",
    "gpt-5.6-terra",
    "gpt-5.6-luna",
    "gpt-5.5",
    "gpt-5.3-codex",
]


def _build_codex_content(prompt: str, attachments: list[Attachment] | None) -> Any:
    """Build the Responses-API `content` for a single user input item.

    Text-only -> plain string. With image attachments -> multimodal array
    of input_text + input_image blocks.
    """
    image_parts: list[dict] = []
    if attachments:
        for att in attachments:
            if att.type.startswith("image/"):
                image_parts.append(
                    {
                        "type": "input_image",
                        "image_url": f"data:{att.type};base64,{att.content}",
                    }
                )
    if not image_parts:
        return prompt
    content: list[dict] = [{"type": "input_text", "text": prompt}]
    content.extend(image_parts)
    return content


def _extract_output_text(data: dict) -> str:
    """Extract final text from a Codex `/responses` payload.

    Prefers top-level `output_text`; falls back to walking `output[]` for
    `message.content[]` blocks of type `output_text`. `reasoning` items are
    ignored.
    """
    output_text = data.get("output_text")
    if isinstance(output_text, str) and output_text:
        return output_text
    texts: list[str] = []
    output = data.get("output", [])
    if isinstance(output, list):
        for item in output:
            if not isinstance(item, dict):
                continue
            if item.get("type") == "reasoning":
                continue
            content = item.get("content", [])
            if not isinstance(content, list):
                continue
            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get("type") in ("output_text", "text"):
                    t = block.get("text", "")
                    if isinstance(t, str) and t:
                        texts.append(t)
    return "".join(texts)


def _extract_stream_delta(data: dict) -> str:
    """Extract delta text from a Codex SSE event payload."""
    dtype = str(data.get("type", ""))
    if "response.output_text.delta" in dtype:
        delta = data.get("delta", "")
        if isinstance(delta, str) and delta:
            return delta
    if dtype in ("response.output_text.done", "response.completed"):
        text = data.get("text", "")
        if isinstance(text, str) and text:
            # `done` events carry the full text; deltas already streamed it,
            # so ignore to avoid duplication. Only used when no deltas came.
            return ""
    # Generic fallback: plain `delta` string field.
    delta = data.get("delta")
    if isinstance(delta, str) and delta and "output_text" in dtype:
        return delta
    return ""


def _map_codex_error(e: httpx.HTTPStatusError, base: str) -> HTTPException | None:
    code = e.response.status_code if e.response is not None else None
    if code == status.HTTP_401_UNAUTHORIZED:
        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed (401): Invalid Codex token for {base}",
        )
    if code in (status.HTTP_402_PAYMENT_REQUIRED, status.HTTP_403_FORBIDDEN):
        return HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Codex entitlement missing ({code}): subscription/account cannot access this model",
        )
    if code == status.HTTP_429_TOO_MANY_REQUESTS:
        return HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limited (429): Too many requests to {base}",
        )
    return None


class CodexClient(ProviderClient):
    def _base(self, endpoint: str) -> str:
        return endpoint.rstrip("/") if endpoint else DEFAULT_BASE

    def _headers(self, api_key: str, account_id: str = "") -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        if account_id:
            headers["ChatGPT-Account-Id"] = account_id
        return headers

    async def list_models(self, endpoint: str, api_key: str) -> list[str]:
        # Curated subscription model list; bare ids only (no `openai/` aliases).
        return list(CODEX_MODELS)

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
        account_id: str = "",
    ) -> str:
        base = self._base(endpoint)
        url = f"{base}/responses"
        headers = self._headers(api_key, account_id)
        payload = {
            "model": model.strip(),
            "input": [{"role": "user", "content": _build_codex_content(prompt, attachments)}],
            "stream": False,
            "store": False,
        }
        # max_tokens/temperature are accepted best-effort; the Responses API
        # may ignore them for some models, so include only when useful.
        if max_tokens:
            payload["max_output_tokens"] = max_tokens
        client = get_shared_client(timeout)
        async with _SEMAPHORE:
            try:
                resp = await client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                return _extract_output_text(resp.json())
            except httpx.HTTPStatusError as e:
                mapped = _map_codex_error(e, base)
                if mapped is not None:
                    raise mapped from e
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
        timeout: int = 120,
        account_id: str = "",
    ) -> AsyncGenerator[str, None]:
        base = self._base(endpoint)
        url = f"{base}/responses"
        headers = self._headers(api_key, account_id)
        headers["Accept"] = "text/event-stream"
        payload = {
            "model": model.strip(),
            "input": [{"role": "user", "content": _build_codex_content(prompt, attachments)}],
            "stream": True,
            "store": False,
        }
        if max_tokens:
            payload["max_output_tokens"] = max_tokens
        client = get_shared_client(timeout)
        async with _SEMAPHORE:
            try:
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
                        if not isinstance(data, dict):
                            continue
                        delta = _extract_stream_delta(data)
                        if delta:
                            yield delta
            except httpx.HTTPStatusError as e:
                mapped = _map_codex_error(e, base)
                if mapped is not None:
                    raise mapped from e
                raise
