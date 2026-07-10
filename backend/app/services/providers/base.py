from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator


class ProviderClient(ABC):
    @abstractmethod
    async def list_models(self, endpoint: str, api_key: str) -> list[str]:
        raise NotImplementedError

    @abstractmethod
    async def chat(
        self,
        endpoint: str,
        api_key: str,
        model: str,
        prompt: str,
        max_tokens: int,
        temperature: float,
    ) -> str:
        raise NotImplementedError

    async def chat_stream(
        self,
        endpoint: str,
        api_key: str,
        model: str,
        prompt: str,
        max_tokens: int,
        temperature: float,
    ) -> AsyncGenerator[str, None]:
        full = await self.chat(endpoint, api_key, model, prompt, max_tokens, temperature)
        yield full
