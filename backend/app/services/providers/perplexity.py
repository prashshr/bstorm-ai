import asyncio
import json
from collections.abc import AsyncGenerator

from app.services.http_client import get_shared_client
from app.services.providers.base import ProviderClient

_SEMAPHORE = asyncio.Semaphore(8)


class PerplexityClient(ProviderClient):
    async def list_models(self, endpoint: str, api_key: str) -> list[str]:
        sonar_models = [
            "sonar",
            "sonar-pro",
            "sonar-reasoning",
            "sonar-reasoning-pro",
            "sonar-deep-research",
            "r1-1776"
        ]

        # Try to dynamically load the Agent API models from Perplexity
        base = endpoint.rstrip("/") if endpoint else "https://api.perplexity.ai"
        url = f"{base}/v1/models"

        try:
            client = get_shared_client(15)
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                rows = data.get("data", [])
                agent_models = []
                for r in rows:
                    mid = r.get("id")
                    if mid and isinstance(mid, str):
                        agent_models.append(mid)
                if agent_models:
                    # Return union of sonar and agent models sorted
                    return sorted(list(set(sonar_models + agent_models)))
        except Exception:
            pass

        return sonar_models

    async def chat(
        self,
        endpoint: str,
        api_key: str,
        model: str,
        prompt: str,
        max_tokens: int,
        temperature: float,
        attachments=None,
        timeout: int = 120,
    ) -> str:
        base = endpoint.rstrip("/") if endpoint else "https://api.perplexity.ai"
        is_third_party = "/" in model

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        if is_third_party:
            # Perplexity Agent API (multi-provider routing)
            if base.endswith("/v1"):
                url = f"{base}/agent"
            elif base.endswith("/chat/completions"):
                url = base.replace("/chat/completions", "/v1/agent")
            else:
                url = f"{base}/v1/agent"

            payload = {
                "model": model,
                "input": prompt,
                "max_output_tokens": max_tokens,
                "temperature": temperature,
            }
        else:
            # Native Sonar completions
            if not base.endswith("/v1") and not base.endswith("/chat/completions"):
                url = f"{base}/chat/completions"
            elif base.endswith("/v1"):
                url = f"{base}/chat/completions"
            else:
                url = base

            payload = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                "temperature": temperature,
            }

        client = get_shared_client(timeout)
        async with _SEMAPHORE:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        if is_third_party:
            # Extract output text from Agent API response structure
            output_list = data.get("output", [])
            if output_list and isinstance(output_list, list):
                content_list = output_list[0].get("content", [])
                if content_list and isinstance(content_list, list):
                    for block in content_list:
                        if isinstance(block, dict) and "text" in block:
                            return block["text"] or ""
            return ""
        else:
            # Native Sonar parsing
            choices = data.get("choices", [])
            if not choices:
                return ""
            message = choices[0].get("message", {})
            return message.get("content", "") or ""

    async def chat_stream(
        self,
        endpoint: str,
        api_key: str,
        model: str,
        prompt: str,
        max_tokens: int,
        temperature: float,
        attachments=None,
        timeout: int = 120,
    ) -> AsyncGenerator[str, None]:
        base = endpoint.rstrip("/") if endpoint else "https://api.perplexity.ai"
        is_third_party = "/" in model
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        }
        client = get_shared_client(timeout)

        if is_third_party:
            # Agent API has no documented SSE delta shape here; fall back to
            # buffered chat and yield the full text as a single delta so the
            # proxy SSE contract (delta strings) is preserved.
            full = await self.chat(
                endpoint, api_key, model, prompt, max_tokens, temperature, attachments, timeout
            )
            if full:
                yield full
            return

        if not base.endswith("/v1") and not base.endswith("/chat/completions"):
            url = f"{base}/chat/completions"
        elif base.endswith("/v1"):
            url = f"{base}/chat/completions"
        else:
            url = base
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
        }
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
                    choices = data.get("choices", [])
                    if not choices:
                        continue
                    delta = choices[0].get("delta", {}) or {}
                    text = (
                        delta.get("content")
                        or delta.get("text")
                        or delta.get("reasoning")
                        or delta.get("reasoning_content")
                        or ""
                    )
                    if text:
                        yield str(text)
