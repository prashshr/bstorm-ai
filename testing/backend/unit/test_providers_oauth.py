import time
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi import HTTPException

from app.api.routes.providers_oauth import (
    _COPILOT_PENDING,
    _OPENROUTER_PENDING,
    _OPENROUTER_RESULTS,
    _OPENROUTER_STATES,
    _poll_copilot_once,
    _poll_openrouter,
    copilot_start,
    openrouter_start,
)
from app.services.typesafe_service import classify_oauth_error


from starlette.requests import Request


class TestCopilotOAuthThrottling:
    @pytest.mark.asyncio
    async def test_poll_throttles_within_interval(self):
        poll_token = "test-copilot-token-123"
        _COPILOT_PENDING[poll_token] = {
            "device_code": "dev-code-123",
            "user_code": "1234-5678",
            "user_id": 1,
            "created_at": time.time(),
            "interval": 5,
            "last_upstream_poll": time.time(),  # Polled just now
        }

        # Should return pending immediately without making any HTTP request
        with patch("httpx.AsyncClient.post") as mock_post:
            res = await _poll_copilot_once(MagicMock(), poll_token=poll_token, user_id=1, uek=None)
            assert res == {"status": "pending"}
            mock_post.assert_not_called()

    @pytest.mark.asyncio
    async def test_poll_slow_down_increases_interval(self):
        poll_token = "test-copilot-token-slowdown"
        _COPILOT_PENDING[poll_token] = {
            "device_code": "dev-code-123",
            "user_code": "1234-5678",
            "user_id": 1,
            "created_at": time.time(),
            "interval": 5,
            "last_upstream_poll": 0.0,  # Ready to poll
        }

        fake_resp = MagicMock()
        fake_resp.status_code = 200
        fake_resp.json.return_value = {"error": "slow_down", "interval": 10}

        with patch("httpx.AsyncClient.post", AsyncMock(return_value=fake_resp)):
            res = await _poll_copilot_once(MagicMock(), poll_token=poll_token, user_id=1, uek=None)
            assert res == {"status": "pending"}
            # Interval should be updated to 10
            assert _COPILOT_PENDING[poll_token]["interval"] >= 10


class TestOpenRouterOAuthFlow:
    @pytest.mark.asyncio
    async def test_openrouter_start_generates_pkce_url(self):
        mock_user = MagicMock(id=42)
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/providers/oauth/openrouter/start",
            "headers": [],
            "client": ("127.0.0.1", 12345),
        }
        req = Request(scope=scope)
        res = await openrouter_start(request=req, current_user=mock_user)
        assert "auth_url" in res
        assert "poll_token" in res
        assert "code_challenge=" in res["auth_url"]
        assert "code_challenge_method=S256" in res["auth_url"]
        assert "openrouter.ai/auth" in res["auth_url"]

        poll_token = res["poll_token"]
        assert poll_token in _OPENROUTER_PENDING
        assert _OPENROUTER_PENDING[poll_token]["user_id"] == 42

    def test_poll_openrouter_returns_pending_and_success(self):
        poll_token = "or-poll-test"
        _OPENROUTER_PENDING[poll_token] = {
            "user_id": 42,
            "state": "state-test",
            "created_at": time.time(),
        }

        # While in pending dict
        res = _poll_openrouter(poll_token=poll_token, user_id=42)
        assert res == {"status": "pending"}

        # When completed into results
        _OPENROUTER_RESULTS[poll_token] = {
            "status": "ok",
            "provider": "openrouter",
            "account": "test-account",
            "user_id": 42,
            "created_at": time.time(),
        }
        res_done = _poll_openrouter(poll_token=poll_token, user_id=42)
        assert res_done["status"] == "ok"
        assert res_done["account"] == "test-account"


class TestTypeSafeOAuthDiagnostics:
    @pytest.mark.asyncio
    async def test_classify_oauth_error_fallback(self):
        # When no API key is set, returns fallback gracefully
        res = await classify_oauth_error("copilot", "slow_down: rate limit exceeded")
        assert "category" in res
        assert "actionable_hint" in res
