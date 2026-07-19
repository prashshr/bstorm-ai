from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from typing import List, Optional

from app.schemas.provider_proxy import Attachment


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
        attachments: Optional[List[Attachment]] = None,
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
        attachments: Optional[List[Attachment]] = None,
    ) -> AsyncGenerator[str, None]:
        full = await self.chat(
            endpoint, api_key, model, prompt, max_tokens, temperature, attachments
        )
        yield full
