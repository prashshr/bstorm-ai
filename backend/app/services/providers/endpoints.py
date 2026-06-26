"""Canonical API endpoints for known OpenAI-compatible providers.

When a user enters an endpoint URL, it's normalized to the canonical form
for their provider so that model discovery and chat requests work correctly.
Unknown providers are left as-is (with runtime retry fallback).
"""

from urllib.parse import urlparse

# Mapping of known provider hostnames to their canonical base endpoint URLs.
# These are the correct paths that work for BOTH model listing AND chat completion.
PROVIDER_ENDPOINTS: dict[str, str] = {
    "openai.com": "https://api.openai.com/v1",
    "openrouter.ai": "https://api.openrouter.ai/v1",
    "perplexity.ai": "https://api.perplexity.ai",
    "groq.com": "https://api.groq.com/openai/v1",
    "together.xyz": "https://api.together.xyz/v1",
    "mistral.ai": "https://api.mistral.ai/v1",
    "deepseek.com": "https://api.deepseek.com/v1",
    "x.ai": "https://api.x.ai/v1",
    "fireworks.ai": "https://api.fireworks.ai/inference/v1",
    "cohere.com": "https://api.cohere.com/v1",
}


def normalize_endpoint(raw_endpoint: str) -> str:
    """Normalize a user-provided endpoint to its canonical form.

    For known providers, returns the correct base URL so both model discovery
    and chat completions work without path guesswork.
    For unknown providers, returns the original input (with trailing slash stripped).
    """
    if not raw_endpoint:
        return raw_endpoint

    raw_endpoint = raw_endpoint.strip().rstrip("/")

    # Extract hostname from URL — handle both "https://host/path" and bare "host"
    parsed = urlparse(raw_endpoint)
    hostname = parsed.netloc or parsed.path.split("/")[0]

    for domain, canonical in PROVIDER_ENDPOINTS.items():
        if domain in hostname:
            return canonical

    return raw_endpoint
