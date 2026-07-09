import pytest


class TestProviders:
    def test_save_provider_credential(self, client, auth_headers, provider_payload):
        resp = client.post("/api/providers", json=provider_payload, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["provider"] == "openai"
        assert data["has_key"] is True
        assert "api_key" not in data

    def test_list_providers(self, client, auth_headers, provider_payload):
        client.post("/api/providers", json=provider_payload, headers=auth_headers)
        resp = client.get("/api/providers", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert any(p["provider"] == "openai" for p in data)
        for p in data:
            assert "api_key" not in p
            assert "has_key" in p

    def test_update_existing_provider(self, client, auth_headers):
        client.post(
            "/api/providers",
            json={"provider": "openai", "api_key": "old-key", "endpoint": ""},
            headers=auth_headers,
        )
        resp = client.post(
            "/api/providers",
            json={"provider": "openai", "api_key": "new-key", "endpoint": "https://custom.ai/v1"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["has_key"] is True

    def test_save_provider_no_auth(self, client, provider_payload):
        resp = client.post("/api/providers", json=provider_payload)
        assert resp.status_code == 401

    def test_discover_models_no_key(self, client, auth_headers):
        resp = client.get("/api/providers/openai/models", headers=auth_headers)
        assert resp.status_code == 404

    def test_discover_models_with_key(self, client, auth_headers):
        client.post(
            "/api/providers",
            json={"provider": "openai", "api_key": "sk-test", "endpoint": ""},
            headers=auth_headers,
        )
        resp = client.get("/api/providers/openai/models", headers=auth_headers)
        assert resp.status_code in (200, 502)

    def test_list_providers_empty(self, client, auth_headers):
        resp = client.get("/api/providers", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_multiple_providers(self, client, auth_headers):
        providers = [
            ("openai", "sk-1"),
            ("anthropic", "sk-ant-1"),
            ("google", "google-key-1"),
        ]
        for prov, key in providers:
            resp = client.post(
                "/api/providers",
                json={"provider": prov, "api_key": key, "endpoint": ""},
                headers=auth_headers,
            )
            assert resp.status_code == 200

        resp = client.get("/api/providers", headers=auth_headers)
        data = resp.json()
        assert len(data) == 3

    def test_provider_data_isolation(self, client, auth_headers, second_user_headers):
        client.post(
            "/api/providers",
            json={"provider": "openai", "api_key": "sk-user1", "endpoint": ""},
            headers=auth_headers,
        )
        resp = client.get("/api/providers", headers=second_user_headers)
        assert resp.json() == []
