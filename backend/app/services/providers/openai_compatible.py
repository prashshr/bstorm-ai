import httpx

from app.services.providers.base import ProviderClient


class OpenAICompatibleClient(ProviderClient):
    async def list_models(self, endpoint: str, api_key: str) -> list[str]:
        base = endpoint.rstrip("/") if endpoint else "https://api.openai.com/v1"
        url = f"{base}/models"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, headers=headers)
            # Some providers (e.g. Perplexity) don't use /v1 — retry without it on 404
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

    async def chat(
        self,
        endpoint: str,
        api_key: str,
        model: str,
        prompt: str,
        max_tokens: int,
        temperature: float,
    ) -> str:
        base = endpoint.rstrip("/") if endpoint else "https://api.openai.com/v1"
        url = f"{base}/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        async with httpx.AsyncClient(timeout=60) as client:
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
