from abc import ABC, abstractmethod


class ProviderClient(ABC):
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
