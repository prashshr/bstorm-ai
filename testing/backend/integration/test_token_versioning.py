"""Access-token versioning (issue 5B).

Password change must invalidate every previously issued access token
immediately, including stateless web tokens that carry no session id and so
cannot be revoked through the session store. Every access token now carries a
`token_ver` claim that must equal `users.token_version`.
"""
from uuid import uuid4

from jose import jwt
from fastapi.testclient import TestClient

from app.core.config import settings


def _decode(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


def _register(http: TestClient, password: str = "testpass123", **extra) -> tuple[str, str, str]:
    email = f"tokv_{uuid4().hex[:16]}@t.com"
    resp = http.post(
        "/api/auth/register",
        json={"email": email, "password": password, **extra},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    return email, body["access_token"], body["refresh_token"]


class TestTokenVersionIssued:
    def test_access_token_carries_token_version(self, client: TestClient):
        _, access, _ = _register(client)
        assert _decode(access).get("token_ver") == 1

    def test_web_token_carries_uek_and_version(self, client: TestClient):
        _, access, _ = _register(client)
        claims = _decode(access)
        assert claims.get("uek"), "web access token must still carry the UEK claim"
        assert claims.get("token_ver") == 1

    def test_mobile_token_carries_sid_and_version(self, client: TestClient):
        _, access, _ = _register(client, client="mobile")
        claims = _decode(access)
        assert claims.get("sid"), "mobile access token must still carry the sid claim"
        assert claims.get("token_ver") == 1

    def test_refresh_issues_the_current_version(self, client: TestClient):
        _, access, refresh = _register(client)
        resp = client.post("/api/auth/refresh", json={"refresh_token": refresh})
        assert resp.status_code == 200, resp.text
        claims = _decode(resp.json()["access_token"])
        assert claims.get("token_ver") == 1
        assert claims.get("sid")


class TestTokenVersionEnforced:
    def test_legacy_token_without_claim_still_accepted(self, client: TestClient):
        """Tokens minted before this change carry no claim. They must keep
        working until their natural expiry so deploying does not sign anyone
        out."""
        _, access, _ = _register(client)
        claims = _decode(access)
        claims.pop("token_ver", None)
        legacy = jwt.encode(claims, settings.jwt_secret, algorithm=settings.jwt_algorithm)
        resp = client.get("/api/user/settings", headers={"Authorization": f"Bearer {legacy}"})
        assert resp.status_code == 200, resp.text

    def test_token_from_an_older_version_is_rejected(self, client: TestClient):
        _, access, _ = _register(client)
        claims = _decode(access)
        claims["token_ver"] = 999
        stale = jwt.encode(claims, settings.jwt_secret, algorithm=settings.jwt_algorithm)
        resp = client.get("/api/user/settings", headers={"Authorization": f"Bearer {stale}"})
        assert resp.status_code == 401

    def test_garbage_version_claim_is_rejected(self, client: TestClient):
        _, access, _ = _register(client)
        claims = _decode(access)
        claims["token_ver"] = "not-a-number"
        broken = jwt.encode(claims, settings.jwt_secret, algorithm=settings.jwt_algorithm)
        resp = client.get("/api/user/settings", headers={"Authorization": f"Bearer {broken}"})
        assert resp.status_code == 401


class TestPasswordChangeRevokesTokens:
    def test_previous_access_token_is_dead_immediately(self, client: TestClient):
        _, access, refresh = _register(client)
        before = {"Authorization": f"Bearer {access}"}
        resp = client.get("/api/user/settings", headers=before)
        assert resp.status_code == 200

        changed = client.post(
            "/api/user/change-password",
            json={
                "current_password": "testpass123",
                "new_password": "CompletelyNew123!",
                "refresh_token": refresh,
            },
            headers=before,
        )
        assert changed.status_code == 200, changed.text
        body = changed.json()
        assert body["token_version"] == 2
        assert isinstance(body["access_token"], str) and body["access_token"]

        # The stolen/old token must stop working at once, not at expiry.
        assert client.get("/api/user/settings", headers=before).status_code == 401
        # ...while the replacement handed back to the acting session works.
        after = {"Authorization": f"Bearer {body['access_token']}"}
        assert client.get("/api/user/settings", headers=after).status_code == 200
        assert _decode(body["access_token"]).get("token_ver") == 2

    def test_refresh_token_of_kept_session_issues_valid_token(self, client: TestClient):
        """The preserved session must be able to renew: its refresh token
        survives, and the new access token carries the bumped version."""
        _, access, refresh = _register(client)
        changed = client.post(
            "/api/user/change-password",
            json={
                "current_password": "testpass123",
                "new_password": "CompletelyNew123!",
                "refresh_token": refresh,
            },
            headers={"Authorization": f"Bearer {access}"},
        )
        assert changed.status_code == 200, changed.text

        refreshed = client.post("/api/auth/refresh", json={"refresh_token": refresh})
        assert refreshed.status_code == 200, refreshed.text
        claims = _decode(refreshed.json()["access_token"])
        assert claims.get("token_ver") == 2
        resp = client.get(
            "/api/user/settings",
            headers={"Authorization": f"Bearer {refreshed.json()['access_token']}"},
        )
        assert resp.status_code == 200, resp.text

    def test_login_after_password_change_returns_a_valid_token(self, client: TestClient):
        """The classic trap: login must stamp the *current* version, or a user
        who changed their password would be signed straight back out."""
        email, access, refresh = _register(client)
        client.post(
            "/api/user/change-password",
            json={
                "current_password": "testpass123",
                "new_password": "CompletelyNew123!",
                "refresh_token": refresh,
            },
            headers={"Authorization": f"Bearer {access}"},
        )
        resp = client.post(
            "/api/auth/login",
            json={"email": email, "password": "CompletelyNew123!"},
        )
        assert resp.status_code == 200, resp.text
        token = resp.json()["access_token"]
        assert _decode(token).get("token_ver") == 2
        assert (
            client.get("/api/user/settings", headers={"Authorization": f"Bearer {token}"}).status_code
            == 200
        )

    def test_mobile_session_gets_a_sid_bearing_replacement(self, client: TestClient):
        """A mobile device resolves its encryption key through the session id.
        The replacement token must keep the sid claim or the device would be
        able to call the API but not decrypt anything."""
        _, access, refresh = _register(client, client="mobile")
        changed = client.post(
            "/api/user/change-password",
            json={
                "current_password": "testpass123",
                "new_password": "CompletelyNew123!",
                "refresh_token": refresh,
            },
            headers={"Authorization": f"Bearer {access}"},
        )
        assert changed.status_code == 200, changed.text
        replacement = changed.json()["access_token"]
        claims = _decode(replacement)
        assert claims.get("sid"), "replacement token for a mobile session must keep its sid"
        assert claims.get("token_ver") == 2
        assert (
            client.get(
                "/api/user/settings", headers={"Authorization": f"Bearer {replacement}"}
            ).status_code
            == 200
        )
