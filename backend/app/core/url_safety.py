"""URL safety validation to prevent SSRF attacks via provider endpoints."""

import ipaddress
import logging
import socket
from urllib.parse import urlparse

logger = logging.getLogger("ai_ensemble.url_safety")


def is_safe_provider_url(url: str) -> bool:
    """Check if a provider endpoint URL resolves to a safe (public) address.

    Rejects private, loopback, link-local, reserved, and multicast addresses.
    This prevents SSRF via custom provider endpoints.
    """
    if not url:
        return True  # Empty endpoint uses provider default

    parsed = urlparse(url)
    if parsed.scheme not in ("https", "http"):
        return False

    hostname = parsed.hostname
    if not hostname:
        return False

    # Allow localhost for local development providers (Ollama, etc.)
    # but log a warning
    if hostname in ("localhost", "127.0.0.1", "::1"):
        logger.warning(f"Provider endpoint uses localhost: {url}")
        return True

    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        return False

    for info in infos:
        try:
            ip = ipaddress.ip_address(info[4][0])
            if ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
                return False
            # Block cloud metadata endpoints
            if ip == ipaddress.ip_address("169.254.169.254"):
                return False
        except ValueError:
            continue

    return True


def validate_endpoint_or_raise(url: str) -> None:
    """Validate an endpoint URL and raise ValueError if unsafe."""
    if not is_safe_provider_url(url):
        raise ValueError(
            f"Endpoint URL '{url}' resolves to a private or restricted address. "
            "Only public provider endpoints are allowed."
        )
