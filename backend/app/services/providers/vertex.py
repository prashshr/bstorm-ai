import contextlib
import os
import tempfile

import httpx
from fastapi import HTTPException, status

from app.services.providers.base import ProviderClient

# Curated Vertex catalog (learned from the reference vertex-ai-models-chat-provider
# project). These are the candidate models; the live, available subset depends on
# what the GCP project actually has access to. We surface the full catalog and let
# the user pick — discovery is effectively the catalog itself since Vertex does not
# expose a public "list all models" endpoint without per-project IAM probing.
VERTEX_CATALOG: list[str] = [
    # Google Gemini (publishers/google)
    "gemini-1.5-flash",
    "gemini-1.5-pro",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gemini-3.5-flash",
    "gemini-3-flash",
    "gemini-3.1-pro",
    # Anthropic Claude on Vertex (publishers/anthropic)
    "claude-opus-4-8",
    "claude-fable-5",
    "claude-sonnet-4-6",
    "claude-haiku-4-5",
]

# Regions to try, in priority order (reference uses these for discovery).
REGION_PRIORITY: list[str] = [
    "global",
    "us-east5",
    "europe-west1",
    "asia-southeast1",
]

# Vendors served by Vertex for the catalog above.
_ANTHROPIC_MODELS = {"claude-opus-4-8", "claude-fable-5", "claude-sonnet-4-6", "claude-haiku-4-5"}


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
        # Vertex does not expose a simple public "list" without per-project IAM
        # probing. We "smart-discover": probe each candidate model against a
        # regionPriority list and return only the models that actually respond
        # for this GCP project (mirrors the jorsm/vertex-ai-models-chat-provider
        # "Smart Discovery" behaviour). This is what makes the health checks
        # show OK instead of KO — only reachable models are surfaced.
        return await self.discover_models()

    async def discover_models(self) -> list[str]:
        """Probe candidate models across all prioritized regions and return the
        union of models reachable in ANY region. Vertex publishes different
        models per region, so we must check every region rather than stopping
        at the first one with a hit — otherwise region-specific models are missed.

        The region that yields the most models is cached for chat() so normal
        traffic uses a single, well-populated host.
        """
        regions = REGION_PRIORITY
        last_err: Exception | None = None
        auth_err: Exception | None = None
        found_by_region: dict[str, list[str]] = {}
        for region in regions:
            working: list[str] = []
            for model in VERTEX_CATALOG:
                try:
                    await self._ping(model, region)
                    working.append(model)
                except Exception as exc:  # noqa: BLE001
                    # Authentication errors are fatal for every region — bubble up.
                    if "401" in str(exc) or "Authentication" in str(exc) or "invalid" in str(exc).lower():
                        auth_err = exc
                        break
                    last_err = exc
                    continue
            if working:
                found_by_region[region] = working

        if not found_by_region:
            if auth_err:
                # Surface the underlying auth error so the UI can report why
                # discovery failed.
                raise auth_err
            if last_err:
                raise last_err
            return []

        # Union of models across all regions (preserve catalog order).
        union: list[str] = []
        for model in VERTEX_CATALOG:
            if any(model in models for models in found_by_region.values()):
                union.append(model)

        # Prefer the region with the most models for chat(); fall back to the
        # first prioritized region that had any hit.
        best_region = max(found_by_region, key=lambda r: len(found_by_region[r]))
        self.region = best_region
        return union

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
                "max_tokens": 1,
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
        async with httpx.AsyncClient(timeout=30) as client:
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
    ) -> str:
        # `api_key` is ignored for Vertex (auth is via ADC); an explicit token
        # passed here would override, but normally empty.
        token = api_key or self._access_token()
        base = self._base_url(model)
        url = f"{base}/models/{model}:generateContent"

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        if model in _ANTHROPIC_MODELS:
            payload = {
                "anthropic_version": "vertex-2023-10-16",
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [{"role": "user", "content": prompt}],
            }
        else:
            payload = {
                "generationConfig": {
                    "temperature": temperature,
                    "maxOutputTokens": max_tokens,
                },
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
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
