"""URL safety validation for provider endpoints."""

import logging
from urllib.parse import urlparse

logger = logging.getLogger("ai_ensemble.url_safety")


def is_safe_provider_url(url: str) -> bool:
    """Check if a provider endpoint URL is a valid HTTP/HTTPS endpoint.

    Blocks sensitive cloud metadata IP (169.254.169.254) to prevent cloud credential leaks,
    while allowing custom self-hosted providers (Omniroute, LiteLLM, Ollama, vLLM, etc.)
    running on local networks, private IPs, or custom internal domains.
    """
    if not url:
        return True  # Empty endpoint uses provider default

    parsed = urlparse(url)
    if parsed.scheme not in ("https", "http"):
        return False

    hostname = parsed.hostname
    if not hostname:
        return False

    # Block sensitive cloud metadata endpoint
    if hostname == "169.254.169.254":
        return False

    return True


def validate_endpoint_or_raise(url: str) -> None:
    """Validate an endpoint URL and raise ValueError if unsafe."""
    if not is_safe_provider_url(url):
        raise ValueError(
            f"Endpoint URL '{url}' is invalid or restricted. "
            "Please provide a valid http:// or https:// provider endpoint URL."
        )
