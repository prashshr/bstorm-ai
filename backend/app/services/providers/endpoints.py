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

# North American provider API endpoints keyed by internal provider name.
# These are defaults applied when a provider is selected in the frontend.
PROVIDER_DEFAULT_ENDPOINTS: dict[str, dict[str, str]] = {
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "models_endpoint": "/models",
        "chat_endpoint": "/chat/completions",
        "embeddings_endpoint": "/embeddings",
        "images_endpoint": "/images/generations",
        "audio_endpoint": "/audio/speech",
        "responses_endpoint": "/responses",
    },
    "anthropic": {
        "base_url": "https://api.anthropic.com",
        "chat_endpoint": "/v1/messages",
        "models_endpoint": "",
    },
    "google": {
        "base_url": "https://generativelanguage.googleapis.com",
        "models_endpoint": "/v1beta/models",
        "chat_endpoint": "/v1beta/models/{model}:generateContent",
    },
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com",
        "models_endpoint": "/v1beta/models",
        "chat_endpoint": "/v1beta/models/{model}:generateContent",
    },
    "openrouter": {
        "base_url": "https://api.openrouter.ai/v1",
        "models_endpoint": "/models",
        "chat_endpoint": "/chat/completions",
    },
    "fireworks": {
        "base_url": "https://api.fireworks.ai/inference/v1",
        "models_endpoint": "/models",
        "chat_endpoint": "/chat/completions",
    },
    "together": {
        "base_url": "https://api.together.xyz/v1",
        "models_endpoint": "/models",
        "chat_endpoint": "/chat/completions",
    },
    "perplexity": {
        "base_url": "https://api.perplexity.ai",
        "models_endpoint": "/models",
        "chat_endpoint": "/chat/completions",
    },
    "mistral": {
        "base_url": "https://api.mistral.ai/v1",
        "models_endpoint": "/models",
        "chat_endpoint": "/chat/completions",
    },
    "xai": {
        "base_url": "https://api.x.ai/v1",
        "models_endpoint": "/models",
        "chat_endpoint": "/chat/completions",
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1",
        "models_endpoint": "/models",
        "chat_endpoint": "/chat/completions",
    },
    "ollama": {
        "base_url": "http://localhost:11434/v1",
        "models_endpoint": "/models",
        "chat_endpoint": "/chat/completions",
    },
    "open-webui": {
        "base_url": "http://localhost:3000/api/v1",
        "models_endpoint": "/models",
        "chat_endpoint": "/chat/completions",
    },
    "azure-openai": {
        "base_url": "https://{resource}.openai.azure.com/openai/deployments/{deployment}",
        "models_endpoint": "",
        "chat_endpoint": "/chat/completions?api-version=2024-02-15-preview",
        "embeddings_endpoint": "/embeddings?api-version=2024-02-15-preview",
        "images_endpoint": "/images/generations?api-version=2024-02-15-preview",
    },
    "vertex": {
        "base_url": "https://{region}-aiplatform.googleapis.com",
        "models_endpoint": "/v1beta1/models",
        "chat_endpoint": "/v1beta1/models/{model}:generateContent",
    },
    "nvidia": {
        "base_url": "https://integrate.api.nvidia.com/v1",
        "models_endpoint": "/models",
        "chat_endpoint": "/chat/completions",
    },
}


def get_provider_default_endpoints(provider: str) -> dict[str, str]:
    """Get default endpoint configuration for a provider.

    Returns a dict with keys like 'base_url', 'models_endpoint', 'chat_endpoint', etc.
    Returns an empty dict if the provider is unknown.
    """
    return PROVIDER_DEFAULT_ENDPOINTS.get(provider.lower(), {})


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
