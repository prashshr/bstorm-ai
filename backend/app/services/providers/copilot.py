"""GitHub Copilot subscription client.

Provider key: `copilot`
Auth: The stored access_token is the user's GitHub OAuth token (ghu_...).
Copilot requires exchanging this token for an ephemeral Copilot session token
via https://api.github.com/copilot_internal/v2/token (valid for ~30 minutes).
Requests are forwarded to https://api.githubcopilot.com/chat/completions.
"""

import asyncio
import json
import time
from collections.abc import AsyncGenerator

import httpx
from fastapi import HTTPException, status

from app.schemas.provider_proxy import Attachment
from app.services.http_client import get_shared_client
from app.services.providers.base import ProviderClient

_SEMAPHORE = asyncio.Semaphore(8)

DEFAULT_COPILOT_BASE = "https://api.githubcopilot.com"

COPILOT_MODELS: list[str] = [
    "gpt-4o",
    "claude-3.5-sonnet",
    "o1-preview",
    "o1-mini",
    "gpt-4o-mini",
]

# Cache of (copilot_token, expires_at_timestamp) keyed by github_oauth_token
_COPILOT_TOKEN_CACHE: dict[str, tuple[str, float]] = {}


async def get_copilot_session_token(github_oauth_token: str, timeout: float = 15.0) -> str:
    """Exchange a GitHub OAuth token for a Copilot session token."""
    now = time.time()
    cached = _COPILOT_TOKEN_CACHE.get(github_oauth_token)
    if cached and cached[1] > now + 60:
        return cached[0]

    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            resp = await client.get(
                "https://api.github.com/copilot_internal/v2/token",
                headers={
                    "Authorization": f"Bearer {github_oauth_token}",
                    "Accept": "application/json",
                    "Editor-Version": "vscode/1.85.1",
                    "Editor-Plugin-Version": "copilot-chat/0.12.0",
                    "User-Agent": "GitHubCopilotChat/0.12.0",
                },
            )
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Could not reach GitHub Copilot token service: {exc}",
            )

    if resp.status_code in (401, 403):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="GitHub Copilot authorization failed. Make sure your GitHub account has an active Copilot subscription.",
        )
    if resp.status_code >= 400:
        raise HTTPException(
            status_code=resp.status_code,
            detail=f"GitHub Copilot token exchange failed ({resp.status_code}): {resp.text[:250]}",
        )

    try:
        data = resp.json()
        token = data.get("token")
        expires_at = float(data.get("expires_at", now + 1800))
        if not token:
            raise ValueError("No token in response")
        _COPILOT_TOKEN_CACHE[github_oauth_token] = (token, expires_at)
        return token
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to parse Copilot session token: {exc}",
        )


class CopilotClient(ProviderClient):
    """GitHub Copilot client utilizing the official Copilot chat completions endpoint."""

    def _base(self, endpoint: str) -> str:
        ep = (endpoint or "").strip().rstrip("/")
        return ep if ep else DEFAULT_COPILOT_BASE

    async def list_models(
        self, endpoint: str = "", api_key: str = "", oauth_token: str = ""
    ) -> list[str]:
        return list(COPILOT_MODELS)

    def _headers(self, copilot_token: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {copilot_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Editor-Version": "vscode/1.85.1",
            "Editor-Plugin-Version": "copilot-chat/0.12.0",
            "Openai-Organization": "github-copilot",
            "Copilot-Integration-Id": "vscode-chat",
            "User-Agent": "GitHubCopilotChat/0.12.0",
        }

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
        account_id: str = "",
    ) -> str:
        github_token = oauth_token or api_key
        if not github_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="GitHub Copilot requires authentication. Connect Copilot in Provider settings.",
            )
        copilot_token = await get_copilot_session_token(github_token, timeout=15.0)
        base = self._base(endpoint)
        url = f"{base}/chat/completions"
        headers = self._headers(copilot_token)

        messages = [{"role": "user", "content": prompt}]
        payload = {
            "model": model.strip(),
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }

        client = get_shared_client(timeout)
        async with _SEMAPHORE:
            try:
                resp = await client.post(url, json=payload, headers=headers)
                if resp.status_code >= 400:
                    err_msg = resp.text[:300]
                    raise HTTPException(
                        status_code=resp.status_code,
                        detail=f"Copilot API error ({resp.status_code}): {err_msg}",
                    )
                data = resp.json()
                choices = data.get("choices", [])
                if choices:
                    return choices[0].get("message", {}).get("content", "")
                return ""
            except httpx.RequestError as exc:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Could not reach Copilot endpoint: {exc}",
                )

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
        account_id: str = "",
    ) -> AsyncGenerator[str, None]:
        github_token = oauth_token or api_key
        if not github_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="GitHub Copilot requires authentication. Connect Copilot in Provider settings.",
            )
        copilot_token = await get_copilot_session_token(github_token, timeout=15.0)
        base = self._base(endpoint)
        url = f"{base}/chat/completions"
        headers = self._headers(copilot_token)
        headers["Accept"] = "text/event-stream"

        messages = [{"role": "user", "content": prompt}]
        payload = {
            "model": model.strip(),
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }

        client = get_shared_client(timeout)
        async with _SEMAPHORE:
            async with client.stream("POST", url, json=payload, headers=headers) as resp:
                if resp.status_code >= 400:
                    body = await resp.aread()
                    err_detail = body.decode("utf-8", errors="replace")[:500]
                    raise HTTPException(
                        status_code=resp.status_code,
                        detail=f"Copilot API error ({resp.status_code}): {err_detail}",
                    )
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
                    if choices:
                        delta = choices[0].get("delta", {})
                        content = delta.get("content")
                        if content:
                            yield content
