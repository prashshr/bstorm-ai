import httpx
from fastapi import HTTPException, status
from app.services.providers.base import ProviderClient

class VertexClient(ProviderClient):
    async def list_models(self, endpoint: str, api_key: str) -> list[str]:
        # Return standard active GCP Vertex Gemini models
        return [
            "gemini-1.5-flash",
            "gemini-1.5-pro",
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",
            "gemini-2.5-flash",
            "gemini-2.5-pro",
            "gemini-3.5-flash"
        ]

    async def chat(
        self,
        endpoint: str,
        api_key: str,
        model: str,
        prompt: str,
        max_tokens: int,
        temperature: float,
    ) -> str:
        # Default endpoint constructs to us-central1
        base = endpoint.rstrip("/") if endpoint else "https://us-central1-aiplatform.googleapis.com/v1/projects/my-project/locations/us-central1/publishers/google"
        url = f"{base}/models/{model}:generateContent"
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
            "contents": [{"parts": [{"text": prompt}]}],
        }
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        candidates = data.get("candidates", [])
        if not candidates:
            return ""
        parts = candidates[0].get("content", {}).get("parts", [])
        if not parts:
            return ""
        return parts[0].get("text", "")
