import httpx
from fastapi import HTTPException, status
from app.services.providers.base import ProviderClient

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
            async with httpx.AsyncClient(timeout=15) as client:
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
            
        async with httpx.AsyncClient(timeout=150) as client:
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
