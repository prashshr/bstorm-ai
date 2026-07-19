import httpx

from app.schemas.provider_proxy import Attachment
from app.services.providers.base import ProviderClient


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
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        content = data.get("content", [])
        if not content:
            return ""
        first = content[0]
        return first.get("text", "")
