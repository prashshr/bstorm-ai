import pytest


class TestAuth:
    def test_register_success(self, client):
        resp = client.post(
            "/api/auth/register",
            json={"email": "new@test.com", "password": "securepass123"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_register_duplicate_email(self, client):
        email = "dupe@test.com"
        resp1 = client.post(
            "/api/auth/register",
            json={"email": email, "password": "securepass123"},
        )
        assert resp1.status_code == 200
        resp2 = client.post(
            "/api/auth/register",
            json={"email": email, "password": "anotherpass123"},
        )
        assert resp2.status_code == 409

    def test_register_invalid_email(self, client):
        resp = client.post(
            "/api/auth/register",
            json={"email": "not-an-email", "password": "securepass123"},
        )
        assert resp.status_code == 422

    def test_register_short_password(self, client):
        resp = client.post(
            "/api/auth/register",
            json={"email": "short@test.com", "password": "short"},
        )
        assert resp.status_code == 422

    def test_login_success(self, client):
        client.post(
            "/api/auth/register",
            json={"email": "login@test.com", "password": "loginpass123"},
        )
        resp = client.post(
            "/api/auth/login",
            json={"email": "login@test.com", "password": "loginpass123"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client):
        client.post(
            "/api/auth/register",
            json={"email": "wrong@test.com", "password": "correctpass123"},
        )
        resp = client.post(
            "/api/auth/login",
            json={"email": "wrong@test.com", "password": "wrongpass123"},
        )
        assert resp.status_code == 401

    def test_login_nonexistent_user(self, client):
        resp = client.post(
            "/api/auth/login",
            json={"email": "nobody@test.com", "password": "somepass123"},
        )
        assert resp.status_code == 401

    def test_unauthenticated_access(self, client):
        resp = client.get("/api/discussions")
        assert resp.status_code == 401

    def test_invalid_token(self, client):
        resp = client.get(
            "/api/discussions",
            headers={"Authorization": "Bearer invalid-token-here"},
        )
        assert resp.status_code == 401

    def test_health_endpoint_no_auth(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}
