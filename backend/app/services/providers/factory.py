from app.services.providers.anthropic import AnthropicClient
from app.services.providers.base import ProviderClient
from app.services.providers.gemini import GeminiClient
from app.services.providers.openai_compatible import OpenAICompatibleClient


PROVIDER_ALIASES: dict[str, str] = {
    "openai": "openai-compatible",
    "openrouter": "openai-compatible",
    "azure-openai": "openai-compatible",
    "openai-compatible": "openai-compatible",
    "anthropic": "anthropic",
    "google": "gemini",
    "gemini": "gemini",
    "fireworks": "openai-compatible",
    "together": "openai-compatible",
    "perplexity": "openai-compatible",
    "mistral": "openai-compatible",
    "xai": "openai-compatible",
    "deepseek": "openai-compatible",
    "ollama": "openai-compatible",
    "open-webui": "openai-compatible",
    "vertex": "gemini",
    "nvidia": "openai-compatible",
}


def get_provider_client(provider: str) -> ProviderClient:
    normalized = PROVIDER_ALIASES.get(provider.lower(), "openai-compatible")
    if normalized == "anthropic":
        return AnthropicClient()
    if normalized == "gemini":
        return GeminiClient()
    return OpenAICompatibleClient()
