import asyncio
import json
import random
import re
from collections.abc import AsyncGenerator
from typing import Any

import httpx
from fastapi import HTTPException, status

from app.schemas.provider_proxy import Attachment
from app.services.http_client import get_shared_client
from app.services.providers.base import ProviderClient

_SEMAPHORE = asyncio.Semaphore(8)

_RETRYABLE_STATUS = {429, 502, 503}


async def _sleep_jittered_backoff() -> None:
    await asyncio.sleep(1.0 + random.uniform(0, 0.5))


def _is_reasoning_model(model: str) -> bool:
    return bool(re.search(r"(o1|o3|o4|reasoner|qwq|deepseek-r1)", model, re.I))


def _build_chat_payload(
    model: str,
    content: Any,
    max_tokens: int,
    temperature: float | None = None,
    stream: bool = False,
) -> dict:
    model_clean = model.strip()
    payload: dict[str, Any] = {
        "model": model_clean,
        "messages": [{"role": "user", "content": content}],
    }
    # For reasoning models, omit temperature if it causes issues, or set standard
    if not _is_reasoning_model(model_clean) and temperature is not None:
        payload["temperature"] = temperature
    payload["max_tokens"] = max_tokens
    if stream:
        payload["stream"] = True
    return payload


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


def _extract_openai_content(data: dict) -> str:
    choices = data.get("choices", [])
    if not choices:
        return ""
    message = choices[0].get("message", {})
    content = (
        message.get("content")
        or message.get("text")
        or message.get("reasoning")
        or message.get("reasoning_content")
        or ""
    )
    return str(content) if content else ""


def _extract_openai_delta(data: dict) -> tuple[str, str]:
    """Extract content and thinking from an OpenAI-compatible SSE delta.

    Returns (content, thinking) where either may be empty string.
    Thinking comes from reasoning/reasoning_content fields that some models
    (e.g. DeepSeek R1, QwQ, mimo) stream separately from the final answer.
    """
    choices = data.get("choices", [])
    if not choices:
        return ("", "")
    delta = choices[0].get("delta", {})
    content = delta.get("content") or delta.get("text") or ""
    thinking = delta.get("reasoning") or delta.get("reasoning_content") or ""
    return (str(content) if content else "", str(thinking) if thinking else "")


def _map_http_status_error(e: httpx.HTTPStatusError, base: str, url: str) -> HTTPException | None:
    code = e.response.status_code if e.response is not None else None
    if code == status.HTTP_401_UNAUTHORIZED:
        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed (401): Invalid API key for {base}",
        )
    if code == status.HTTP_404_NOT_FOUND:
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Endpoint not found (404): {url}",
        )
    if code == status.HTTP_502_BAD_GATEWAY:
        return HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Bad Gateway (502): Could not reach the provider at {base}",
        )
    if code == status.HTTP_429_TOO_MANY_REQUESTS:
        return HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limited (429): Too many requests to {base}",
        )
    return None


class OpenAICompatibleClient(ProviderClient):
    USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    def _get_headers(self, api_key: str) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "User-Agent": self.USER_AGENT,
            "HTTP-Referer": "https://ai-ensemble.samkhya.cloud",
            "X-Title": "AI-Ensemble",
        }
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        return headers

    async def list_models(self, endpoint: str, api_key: str) -> list[str]:
        base = endpoint.rstrip("/") if endpoint else "https://api.openai.com/v1"
        url = f"{base}/models"
        headers = self._get_headers(api_key)
        client = get_shared_client(30)
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
                    # Exclude batch-only and internal contributor endpoints
                    if model_id.endswith(":batch") or "-contributor" in model_id or model_id.startswith("~"):
                        continue
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
        timeout: int = 120,
    ) -> str:
        base = endpoint.rstrip("/") if endpoint else "https://api.openai.com/v1"
        url = f"{base}/chat/completions"
        headers = self._get_headers(api_key)
        content = _build_openai_content(prompt, attachments)
        payload = _build_chat_payload(model, content, max_tokens, temperature)

        client = get_shared_client(timeout)
        async with _SEMAPHORE:
            resp: httpx.Response | None = None
            last_error: httpx.HTTPStatusError | None = None
            # ONE retry with ~1s jittered backoff on 429/502/503 only.
            for attempt in range(2):
                try:
                    resp = await client.post(url, json=payload, headers=headers)
                    # Some providers (e.g. Perplexity) don't use /v1 — retry without it on 404
                    if resp.status_code == 404 and "/v1" in base:
                        alt_base = base.replace("/v1", "")
                        alt_url = f"{alt_base}/chat/completions"
                        resp = await client.post(alt_url, json=payload, headers=headers)
                    resp.raise_for_status()
                    last_error = None
                    break
                except httpx.HTTPStatusError as e:
                    last_error = e
                    code = e.response.status_code if e.response is not None else None
                    if code in _RETRYABLE_STATUS and attempt == 0:
                        await _sleep_jittered_backoff()
                        continue
                    break
            if last_error is not None and resp is not None:
                # Re-raise through the existing fallback/mapping path below.
                try:
                    raise last_error
                except httpx.HTTPStatusError as e:
                    body = e.response.text.lower() if e.response is not None else ""
                    # Fallback 1: if provider rejects image attachments for a text-only model, retry with text prompt
                    if e.response.status_code == status.HTTP_400_BAD_REQUEST and attachments and any(
                        k in body for k in ("image", "vision", "multimodal", "unsupported", "content")
                    ):
                        try:
                            fallback_payload = _build_chat_payload(model, prompt, max_tokens, temperature)
                            resp = await client.post(url, json=fallback_payload, headers=headers)
                            resp.raise_for_status()
                            return _extract_openai_content(resp.json())
                        except Exception:
                            pass

                    # Fallback 2: if provider rejects temperature (e.g. reasoning models)
                    if e.response.status_code == status.HTTP_400_BAD_REQUEST and "temperature" in body:
                        try:
                            fallback_payload = {
                                "model": model.strip(),
                                "messages": [{"role": "user", "content": content}],
                                "max_tokens": max_tokens,
                            }
                            resp = await client.post(url, json=fallback_payload, headers=headers)
                            resp.raise_for_status()
                            return _extract_openai_content(resp.json())
                        except Exception:
                            pass

                    # Fallback 3: if provider rejects max_tokens in favor of max_completion_tokens (e.g. newer models)
                    if e.response.status_code == status.HTTP_400_BAD_REQUEST and "max_completion_tokens" in body:
                        try:
                            fallback_payload = {
                                "model": model.strip(),
                                "messages": [{"role": "user", "content": content}],
                                "max_completion_tokens": max_tokens,
                            }
                            resp = await client.post(url, json=fallback_payload, headers=headers)
                            resp.raise_for_status()
                            return _extract_openai_content(resp.json())
                        except Exception:
                            pass

                    mapped = _map_http_status_error(e, base, url)
                    if mapped is not None:
                        raise mapped from e
                    raise
            if resp is None:
                return ""
            try:
                return _extract_openai_content(resp.json())
            except httpx.HTTPStatusError as e:
                body = e.response.text.lower() if e.response is not None else ""
                # Fallback 1: if provider rejects image attachments for a text-only model, retry with text prompt
                if e.response.status_code == status.HTTP_400_BAD_REQUEST and attachments and any(
                    k in body for k in ("image", "vision", "multimodal", "unsupported", "content")
                ):
                    try:
                        fallback_payload = _build_chat_payload(model, prompt, max_tokens, temperature)
                        resp = await client.post(url, json=fallback_payload, headers=headers)
                        resp.raise_for_status()
                        return _extract_openai_content(resp.json())
                    except Exception:
                        pass

                # Fallback 2: if provider rejects temperature (e.g. reasoning models)
                if e.response.status_code == status.HTTP_400_BAD_REQUEST and "temperature" in body:
                    try:
                        fallback_payload = {
                            "model": model.strip(),
                            "messages": [{"role": "user", "content": content}],
                            "max_tokens": max_tokens,
                        }
                        resp = await client.post(url, json=fallback_payload, headers=headers)
                        resp.raise_for_status()
                        return _extract_openai_content(resp.json())
                    except Exception:
                        pass

                # Fallback 3: if provider rejects max_tokens in favor of max_completion_tokens (e.g. newer models)
                if e.response.status_code == status.HTTP_400_BAD_REQUEST and "max_completion_tokens" in body:
                    try:
                        fallback_payload = {
                            "model": model.strip(),
                            "messages": [{"role": "user", "content": content}],
                            "max_completion_tokens": max_tokens,
                        }
                        resp = await client.post(url, json=fallback_payload, headers=headers)
                        resp.raise_for_status()
                        return _extract_openai_content(resp.json())
                    except Exception:
                        pass

                # Handle specific error cases for better error messages
                mapped = _map_http_status_error(e, base, url)
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
    ) -> AsyncGenerator[str, None]:
        base = endpoint.rstrip("/") if endpoint else "https://api.openai.com/v1"
        url = f"{base}/chat/completions"
        headers = self._get_headers(api_key)
        content = _build_openai_content(prompt, attachments)
        payload = _build_chat_payload(model, content, max_tokens, temperature, stream=True)
        client = get_shared_client(timeout)

        async def _drain_openai_stream(resp: httpx.Response):
            async for line in resp.aiter_lines():
                if not line or line.startswith(":"):
                    continue
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str.strip() == "[DONE]":
                        return
                    try:
                        data = json.loads(data_str)
                        content, thinking = _extract_openai_delta(data)
                        if thinking:
                            yield ("thinking_delta", thinking)
                        if content:
                            yield ("delta", content)
                    except json.JSONDecodeError:
                        continue

        async with _SEMAPHORE:
            # ONE retry with ~1s jittered backoff on 429/502/503 for the
            # initial stream setup only.
            last_status_error: httpx.HTTPStatusError | None = None
            for attempt in range(2):
                last_status_error = None
                try:
                    async with client.stream("POST", url, json=payload, headers=headers) as resp:
                        if resp.status_code == 404 and "/v1" in base:
                            alt_base = base.replace("/v1", "")
                            alt_url = f"{alt_base}/chat/completions"
                            async with client.stream("POST", alt_url, json=payload, headers=headers) as resp2:
                                resp2.raise_for_status()
                                async for chunk in _drain_openai_stream(resp2):
                                    yield chunk
                            return
                        resp.raise_for_status()
                        async for chunk in _drain_openai_stream(resp):
                            yield chunk
                    return
                except httpx.HTTPStatusError as e:
                    last_status_error = e
                    code = e.response.status_code if e.response is not None else None
                    if code in _RETRYABLE_STATUS and attempt == 0:
                        await _sleep_jittered_backoff()
                        continue
                    break
            if last_status_error is not None:
                e = last_status_error
                body = e.response.text.lower() if e.response is not None else ""
                if e.response.status_code == status.HTTP_400_BAD_REQUEST and attachments and any(
                    k in body for k in ("image", "vision", "multimodal", "unsupported", "content")
                ):
                    try:
                        fallback_payload = _build_chat_payload(model, prompt, max_tokens, temperature, stream=True)
                        async with client.stream("POST", url, json=fallback_payload, headers=headers) as resp_fallback:
                            resp_fallback.raise_for_status()
                            async for chunk in _drain_openai_stream(resp_fallback):
                                yield chunk
                        return
                    except Exception:
                        pass

                if e.response.status_code == status.HTTP_400_BAD_REQUEST and "temperature" in body:
                    try:
                        fallback_payload = {
                            "model": model.strip(),
                            "messages": [{"role": "user", "content": content}],
                            "max_tokens": max_tokens,
                            "stream": True,
                        }
                        async with client.stream("POST", url, json=fallback_payload, headers=headers) as resp_fallback:
                            resp_fallback.raise_for_status()
                            async for chunk in _drain_openai_stream(resp_fallback):
                                yield chunk
                        return
                    except Exception:
                        pass

                mapped = _map_http_status_error(e, base, url)
                if mapped is not None:
                    raise mapped from e
                raise
