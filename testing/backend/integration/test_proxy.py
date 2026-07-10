import pytest
from unittest.mock import patch, AsyncMock
from app.schemas.provider_proxy import ChatRequest


class TestProxy:
    def test_proxy_chat_no_credentials(self, client, auth_headers):
        resp = client.post(
            "/api/proxy/chat",
            json={
                "provider": "openai",
                "model": "gpt-4",
                "prompt": "Hello",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 404
        assert "credential not found" in resp.json()["detail"].lower()

    def test_proxy_chat_with_rag_context_flag(self, client, auth_headers, discussion_id):
        client.post(
            "/api/providers",
            json={"provider": "openai", "api_key": "sk-test", "endpoint": ""},
            headers=auth_headers,
        )
        resp = client.post(
            "/api/proxy/chat",
            json={
                "provider": "openai",
                "model": "gpt-4",
                "prompt": "Hello",
                "discussion_id": discussion_id,
                "include_rag_context": True,
            },
            headers=auth_headers,
        )
        assert resp.status_code in (200, 401, 502)

    def test_proxy_chat_invalid_discussion_id(self, client, auth_headers):
        client.post(
            "/api/providers",
            json={"provider": "openai", "api_key": "sk-test", "endpoint": ""},
            headers=auth_headers,
        )
        resp = client.post(
            "/api/proxy/chat",
            json={
                "provider": "openai",
                "model": "gpt-4",
                "prompt": "Hello",
                "discussion_id": 99999,
                "include_rag_context": True,
            },
            headers=auth_headers,
        )
        assert resp.status_code in (200, 401, 502)

    def test_proxy_chat_no_auth(self, client):
        resp = client.post(
            "/api/proxy/chat",
            json={"provider": "openai", "model": "gpt-4", "prompt": "Hello"},
        )
        assert resp.status_code == 401

    def test_proxy_chat_invalid_discussion_id(self, client, auth_headers):
        client.post(
            "/api/providers",
            json={"provider": "openai", "api_key": "sk-test", "endpoint": ""},
            headers=auth_headers,
        )
        resp = client.post(
            "/api/proxy/chat",
            json={
                "provider": "openai",
                "model": "gpt-4",
                "prompt": "Hello",
                "discussion_id": 99999,
                "include_rag_context": True,
            },
            headers=auth_headers,
        )
        assert resp.status_code in (200, 401, 502)

    def test_chat_request_schema_validates(self):
        req = ChatRequest(
            provider="openai",
            model="gpt-4",
            prompt="Test prompt",
            discussion_id=42,
            include_rag_context=True,
        )
        assert req.provider == "openai"
        assert req.discussion_id == 42
        assert req.include_rag_context is True

    def test_chat_request_schema_defaults(self):
        req = ChatRequest(
            provider="anthropic",
            model="claude-3",
            prompt="Hello",
        )
        assert req.discussion_id is None
        assert req.include_rag_context is False
        assert req.max_tokens == 1000
        assert req.temperature == 0.7

    def test_proxy_chat_requires_provider(self, client, auth_headers):
        resp = client.post(
            "/api/proxy/chat",
            json={"model": "gpt-4", "prompt": "Hello"},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_proxy_chat_stream_no_credentials(self, client, auth_headers):
        resp = client.post(
            "/api/proxy/chat/stream",
            json={
                "provider": "openai",
                "model": "gpt-4",
                "prompt": "Hello",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 404
        assert "credential not found" in resp.json()["detail"].lower()

    def test_proxy_chat_stream_requires_auth(self, client):
        resp = client.post(
            "/api/proxy/chat/stream",
            json={"provider": "openai", "model": "gpt-4", "prompt": "Hello"},
        )
        assert resp.status_code == 401

    def test_proxy_chat_stream_returns_event_stream(self, client, auth_headers):
        client.post(
            "/api/providers",
            json={"provider": "openai", "api_key": "sk-test", "endpoint": ""},
            headers=auth_headers,
        )
        resp = client.post(
            "/api/proxy/chat/stream",
            json={
                "provider": "openai",
                "model": "gpt-4",
                "prompt": "Hello",
            },
            headers=auth_headers,
        )
        assert resp.status_code in (200, 401, 502)
        if resp.status_code == 200:
            assert resp.headers["content-type"].startswith("text/event-stream")
