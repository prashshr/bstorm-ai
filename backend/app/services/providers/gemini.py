import httpx

from app.services.providers.base import ProviderClient


class GeminiClient(ProviderClient):
    async def list_models(self, endpoint: str, api_key: str) -> list[str]:
        base = endpoint.rstrip("/") if endpoint else "https://generativelanguage.googleapis.com"
        url = f"{base}/v1beta/models?key={api_key}"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url)
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
    ) -> str:
        base = endpoint.rstrip("/") if endpoint else "https://generativelanguage.googleapis.com"
        url = f"{base}/v1beta/models/{model}:generateContent?key={api_key}"
        payload = {
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
            "contents": [{"parts": [{"text": prompt}]}],
        }
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()

        candidates = data.get("candidates", [])
        if not candidates:
            return ""
        parts = candidates[0].get("content", {}).get("parts", [])
        if not parts:
            return ""
        return parts[0].get("text", "")
