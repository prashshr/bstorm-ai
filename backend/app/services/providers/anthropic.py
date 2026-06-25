import httpx

from app.services.providers.base import ProviderClient


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
    ) -> str:
        base = endpoint.rstrip("/") if endpoint else "https://api.anthropic.com"
        url = f"{base}/v1/messages"
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        content = data.get("content", [])
        if not content:
            return ""
        first = content[0]
        return first.get("text", "")
