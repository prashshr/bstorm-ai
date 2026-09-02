import asyncio
import contextlib
import os
import tempfile

import httpx
from fastapi import HTTPException, status

from app.services.providers.base import ProviderClient

# Curated Vertex catalog. These are candidate models available on GCP Vertex AI.
# The discovery probe checks which models are reachable for the given GCP project.
VERTEX_CATALOG: list[str] = [
    # Google Gemini (publishers/google)
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gemini-2.0-flash-001",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite-preview-02-05",
    "gemini-2.0-flash-lite",
    "gemini-1.5-flash-002",
    "gemini-1.5-flash-001",
    "gemini-1.5-flash",
    "gemini-1.5-pro-002",
    "gemini-1.5-pro-001",
    "gemini-1.5-pro",
    # Anthropic Claude on Vertex (publishers/anthropic)
    "claude-3-7-sonnet@20250219",
    "claude-3-5-sonnet-v2@20241022",
    "claude-3-5-sonnet@20240620",
    "claude-3-5-haiku@20241022",
    "claude-3-opus@20240229",
    "claude-3-haiku@20240307",
]

# Regions to try, in priority order (reference uses these for discovery).
REGION_PRIORITY: list[str] = [
    "global",
    "us-east5",
    "europe-west1",
    "asia-southeast1",
]

# Vendors served by Vertex for the catalog above.
_ANTHROPIC_MODELS = {
    "claude-3-7-sonnet@20250219",
    "claude-3-5-sonnet-v2@20241022",
    "claude-3-5-sonnet@20240620",
    "claude-3-5-haiku@20241022",
    "claude-3-opus@20240229",
    "claude-3-haiku@20240307",
}


class VertexClient(ProviderClient):
    # Project/region are injected by the API layer from the stored credential.
    project_id: str | None = None
    region: str | None = None
    # Decrypted Application Default Credentials JSON (service-account key or
    # gcloud user-ADC), supplied per user. When set, it overrides any
    # environment-level ADC for this client.
    adc_json: str | None = None

    # ------------------------------------------------------------------
    # Auth: use Application Default Credentials (ADC). Resolution order:
    #   1. A per-user ADC JSON supplied via the provider form (written to a
    #      temporary credentials file and pointed at by GOOGLE_APPLICATION_CREDENTIALS).
    #   2. Environment-level ADC (GOOGLE_APPLICATION_CREDENTIALS / gcloud ADC)
    #      already configured in the deployment.
    # ------------------------------------------------------------------
    @contextlib.contextmanager
    def _adc_env(self):
        """Temporarily point GOOGLE_APPLICATION_CREDENTIALS at a per-request
        temp file containing the user-supplied ADC JSON, if any. Restores the
        previous environment afterwards so concurrent requests don't clash."""
        if not self.adc_json:
            yield
            return
        prev = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", prefix="vertex-adc-", delete=False
        )
        try:
            tmp.write(self.adc_json)
            tmp.close()
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = tmp.name
            try:
                yield
            finally:
                if prev is None:
                    os.environ.pop("GOOGLE_APPLICATION_CREDENTIALS", None)
                else:
                    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = prev
        finally:
            try:
                os.unlink(tmp.name)
            except OSError:
                pass

    def _access_token(self) -> str:
        project = self.project_id or os.getenv("GOOGLE_CLOUD_PROJECT")
        if not project:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Vertex AI: a GCP Project ID is required. Set it in the provider "
                    "settings (Project ID) or via the GOOGLE_CLOUD_PROJECT env var."
                ),
            )
        try:
            import google.auth
            from google.auth.transport.requests import Request as AuthRequest
        except ImportError:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(
                    "Vertex AI: google-auth is not installed in the backend. "
                    "Add 'google-auth' to requirements and redeploy."
                ),
            )

        with self._adc_env():
            credentials, _ = google.auth.default()
            # ADC credentials may need a refresh to carry a valid token.
            if not credentials.valid:
                try:
                    credentials.refresh(AuthRequest())
                except Exception as exc:  # noqa: BLE001
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail=f"Vertex AI: failed to obtain credentials via ADC: {exc}",
                    )
            if not credentials.token:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Vertex AI: ADC returned no access token. Check GCP auth env/config.",
                )
        return credentials.token

    def _region(self) -> str:
        return (self.region or os.getenv("VERTEX_REGION") or "global").strip() or "global"

    def _base_url(self, model: str) -> str:
        region = self._region()
        project = self.project_id or os.getenv("GOOGLE_CLOUD_PROJECT") or "my-project"
        publisher = "anthropic" if model in _ANTHROPIC_MODELS else "google"
        # us-central1 style region slug for the hostname.
        host_region = "us-central1" if region == "global" else region
        return (
            f"https://{host_region}-aiplatform.googleapis.com/v1"
            f"/projects/{project}/locations/{region}"
            f"/publishers/{publisher}"
        )

    # ------------------------------------------------------------------
    async def list_models(self, endpoint: str, api_key: str) -> list[str]:
        return await self.discover_models()

    async def discover_models(self) -> list[str]:
        """Probe candidate models in parallel across prioritized regions and return
        the list of reachable models. Falls back to default VERTEX_CATALOG if probing yields
        no active models so model search remains populated."""
        found_by_region: dict[str, list[str]] = {}
        auth_err: Exception | None = None

        async def probe_model(model: str, region: str) -> tuple[str, str, bool, Exception | None]:
            try:
                await self._ping(model, region)
                return (model, region, True, None)
            except Exception as exc:  # noqa: BLE001
                return (model, region, False, exc)

        tasks = [
            probe_model(model, region)
            for region in REGION_PRIORITY
            for model in VERTEX_CATALOG
        ]

        results = await asyncio.gather(*tasks)

        for model, region, success, exc in results:
            if success:
                found_by_region.setdefault(region, []).append(model)
            elif exc:
                err_str = str(exc)
                if "401" in err_str or "Authentication" in err_str or "invalid" in err_str.lower():
                    auth_err = exc

        if not found_by_region:
            if auth_err:
                raise auth_err
            # Fall back to catalog so model search is always populated
            return VERTEX_CATALOG

        union: list[str] = []
        for model in VERTEX_CATALOG:
            if any(model in models for models in found_by_region.values()):
                union.append(model)

        best_region = max(found_by_region, key=lambda r: len(found_by_region[r]))
        self.region = best_region
        return union or VERTEX_CATALOG

    async def _ping(self, model: str, region: str) -> None:
        """Minimal generateContent call (maxOutputTokens=1) to verify a model
        is reachable for the given project/region."""
        token = self._access_token()
        publisher = "anthropic" if model in _ANTHROPIC_MODELS else "google"
        host_region = "us-central1" if region == "global" else region
        url = (
            f"https://{host_region}-aiplatform.googleapis.com/v1"
            f"/projects/{self.project_id or os.getenv('GOOGLE_CLOUD_PROJECT')}/locations/{region}"
            f"/publishers/{publisher}/models/{model}:generateContent"
        )
        if model in _ANTHROPIC_MODELS:
            payload = {
                "anthropic_version": "vertex-2023-10-16",
                "max_tokens": 10,
                "messages": [{"role": "user", "content": "ping"}],
            }
        else:
            payload = {
                "contents": [{"role": "user", "parts": [{"text": "ping"}]}],
                "generationConfig": {"maxOutputTokens": 1},
            }
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()

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
        token = api_key or self._access_token()
        base = self._base_url(model)
        url = f"{base}/models/{model}:generateContent"

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        if model in _ANTHROPIC_MODELS:
            blocks = [{"type": "text", "text": prompt}]
            if attachments:
                for att in attachments:
                    if att.type.startswith("image/"):
                        blocks.append(
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": att.type,
                                    "data": att.content,
                                },
                            }
                        )
            payload = {
                "anthropic_version": "vertex-2023-10-16",
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [{"role": "user", "content": blocks}],
            }
        else:
            parts = [{"text": prompt}]
            if attachments:
                for att in attachments:
                    if att.type.startswith("image/"):
                        parts.append(
                            {
                                "inline_data": {
                                    "mime_type": att.type,
                                    "data": att.content,
                                }
                            }
                        )
            payload = {
                "generationConfig": {
                    "temperature": temperature,
                    "maxOutputTokens": max_tokens,
                },
                "contents": [{"role": "user", "parts": parts}],
            }

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        # Gemini response shape
        candidates = data.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            if parts:
                return parts[0].get("text", "")

        # Anthropic-on-Vertex response shape
        if isinstance(data.get("content"), list):
            return "".join(
                part.get("text", "")
                for part in data["content"]
                if isinstance(part, dict)
            )

        return ""
