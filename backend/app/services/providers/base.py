from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from typing import List, Optional, Union

from app.schemas.provider_proxy import Attachment

# Stream chunk type: either a plain string (treated as "delta") or a
# (event_type, content) tuple where event_type is "delta" or "thinking_delta".
StreamChunk = Union[str, tuple[str, str]]


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
        timeout: int = 120,
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
        timeout: int = 120,
    ) -> AsyncGenerator[StreamChunk, None]:
        full = await self.chat(
            endpoint, api_key, model, prompt, max_tokens, temperature, attachments, timeout
        )
        yield full
