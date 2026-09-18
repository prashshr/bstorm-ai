import pytest
from unittest.mock import AsyncMock, patch
from fastapi import HTTPException

from app.services.providers.copilot import CopilotClient, get_copilot_session_token, COPILOT_MODELS
from app.services.providers.factory import get_provider_client


class TestCopilotProvider:
    @pytest.mark.asyncio
    async def test_factory_resolves_copilot_client(self):
        client = get_provider_client("copilot")
        assert isinstance(client, CopilotClient)

    @pytest.mark.asyncio
    async def test_list_models_returns_curated_copilot_models(self):
        client = CopilotClient()
        models = await client.list_models()
        assert "gpt-4o" in models
        assert "claude-3.5-sonnet" in models
        assert len(models) == len(COPILOT_MODELS)

    @pytest.mark.asyncio
    async def test_copilot_session_token_exchange_success(self):
        fake_response = AsyncMock()
        fake_response.status_code = 200
        fake_response.json = lambda: {
            "token": "tid=copilot-test-token;exp=9999999999",
            "expires_at": 9999999999,
        }

        with patch("httpx.AsyncClient.get", return_value=fake_response):
            token = await get_copilot_session_token("ghu_fake_github_oauth_token")
            assert token.startswith("tid=copilot-test-token")

    @pytest.mark.asyncio
    async def test_copilot_session_token_exchange_unauthorized(self):
        fake_response = AsyncMock()
        fake_response.status_code = 401
        fake_response.text = "Unauthorized"

        with patch("httpx.AsyncClient.get", return_value=fake_response):
            with pytest.raises(HTTPException) as exc_info:
                await get_copilot_session_token("ghu_invalid_token")
            assert exc_info.value.status_code == 401
            assert "active Copilot subscription" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_chat_requires_auth_token(self):
        client = CopilotClient()
        with pytest.raises(HTTPException) as exc_info:
            await client.chat(
                endpoint="",
                api_key="",
                model="gpt-4o",
                prompt="Hello",
                max_tokens=100,
                temperature=0.7,
                oauth_token="",
            )
        assert exc_info.value.status_code == 401
        assert "Connect Copilot" in exc_info.value.detail
