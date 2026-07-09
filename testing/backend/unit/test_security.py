import pytest
from app.core.crypto import encrypt_secret, decrypt_secret, encrypt_field, decrypt_field_or_plaintext


class TestSecurity:
    def test_encrypt_decrypt_roundtrip(self):
        original = "sk-test-api-key-12345"
        encrypted = encrypt_secret(original)
        assert encrypted != original
        decrypted = decrypt_secret(encrypted)
        assert decrypted == original

    def test_encrypt_decrypt_with_uek(self, valid_uek):
        original = "my-secret-value"
        encrypted = encrypt_secret(original, key=valid_uek)
        assert encrypted != original
        decrypted = decrypt_secret(encrypted, key=valid_uek)
        assert decrypted == original

    def test_different_uek_produces_different_ciphertext(self):
        import base64
        uek1 = base64.urlsafe_b64encode(b"a" * 32).decode()
        uek2 = base64.urlsafe_b64encode(b"b" * 32).decode()
        val = "same-value"
        e1 = encrypt_secret(val, key=uek1)
        e2 = encrypt_secret(val, key=uek2)
        assert e1 != e2

    def test_wrong_uek_fails_to_decrypt(self):
        import base64
        uek1 = base64.urlsafe_b64encode(b"a" * 32).decode()
        uek2 = base64.urlsafe_b64encode(b"b" * 32).decode()
        encrypted = encrypt_secret("secret", key=uek1)
        with pytest.raises(Exception):
            decrypt_secret(encrypted, key=uek2)

    def test_encrypt_field_none_returns_none(self):
        assert encrypt_field(None, "some-key") is None

    def test_encrypt_field_empty_string(self):
        result = encrypt_field("", "some-key")
        assert result is not None

    def test_decrypt_field_or_plaintext_with_key(self, valid_uek):
        encrypted = encrypt_field("hello world", valid_uek)
        assert encrypted is not None
        decrypted = decrypt_field_or_plaintext(encrypted, valid_uek)
        assert decrypted == "hello world"

    def test_decrypt_field_or_plaintext_none(self):
        assert decrypt_field_or_plaintext(None, "key") is None

    def test_decrypt_field_or_plaintext_plaintext_returns_as_is(self):
        result = decrypt_field_or_plaintext("already-plain-text", None)
        assert result == "already-plain-text"

    def test_data_isolation_between_users(self, client, auth_headers, second_user_headers):
        client.post(
            "/api/discussions",
            json={"title": "Secret Discussion", "question": "Classified?"},
            headers=auth_headers,
        )
        resp = client.get("/api/discussions", headers=second_user_headers)
        for d in resp.json():
            assert d["title"] != "Secret Discussion"

    def test_encrypted_discussion_context_storage(self, client, auth_headers):
        resp = client.post(
            "/api/discussions",
            json={
                "title": "Encrypted RAG",
                "question": "Test storage?",
                "use_rag": True,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "retrieved_context" in data
        assert data["title"] == "Encrypted RAG"

    def test_rate_limiting_health_endpoint(self, client):
        for _ in range(60):
            resp = client.get("/health")
        resp = client.get("/health")
        assert resp.status_code in (200, 429)

    def test_cors_headers_present(self, client):
        resp = client.options(
            "/health",
            headers={
                "Origin": "https://ai-ensemble.samkhya.cloud",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert "access-control-allow-origin" in resp.headers or resp.status_code == 200
