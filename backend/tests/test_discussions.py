import pytest


class TestDiscussions:
    def test_create_discussion(self, client, auth_headers):
        resp = client.post(
            "/api/discussions",
            json={"title": "My Test", "question": "Best smartphones 2026?"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert data["title"] == "My Test"
        assert data["question"] == "Best smartphones 2026?"
        assert data["status"] == "new"

    def test_create_discussion_with_rag(self, client, auth_headers):
        resp = client.post(
            "/api/discussions",
            json={
                "title": "RAG Test",
                "question": "Best laptops under 1000?",
                "use_rag": True,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert "retrieved_context" in data

    def test_create_discussion_with_deep_research(self, client, auth_headers):
        resp = client.post(
            "/api/discussions",
            json={
                "title": "Deep Research",
                "question": "Latest AI trends?",
                "use_rag": True,
                "deep_research": True,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200

    def test_list_discussions(self, client, auth_headers):
        client.post(
            "/api/discussions",
            json={"title": "D1", "question": "Q1"},
            headers=auth_headers,
        )
        client.post(
            "/api/discussions",
            json={"title": "D2", "question": "Q2"},
            headers=auth_headers,
        )
        resp = client.get("/api/discussions", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 2
        assert data[0]["created_at"] >= data[1]["created_at"]

    def test_create_discussion_no_auth(self, client):
        resp = client.post(
            "/api/discussions",
            json={"title": "No Auth", "question": "Test?"},
        )
        assert resp.status_code == 401

    def test_discussion_isolation(self, client, auth_headers, second_user_headers):
        client.post(
            "/api/discussions",
            json={"title": "User1 Discussion", "question": "Q1"},
            headers=auth_headers,
        )
        resp = client.get("/api/discussions", headers=second_user_headers)
        for d in resp.json():
            assert d["title"] != "User1 Discussion"

    def test_create_message(self, client, auth_headers, discussion_id):
        resp = client.post(
            "/api/discussions/messages",
            json={
                "discussion_id": discussion_id,
                "round_number": 1,
                "model": "gpt-4",
                "role": "assistant",
                "content": "AI stands for Artificial Intelligence.",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["content"] == "AI stands for Artificial Intelligence."
        assert data["discussion_id"] == discussion_id

    def test_list_messages(self, client, auth_headers, discussion_id):
        client.post(
            "/api/discussions/messages",
            json={
                "discussion_id": discussion_id,
                "round_number": 1,
                "model": "gpt-4",
                "role": "assistant",
                "content": "Message 1",
            },
            headers=auth_headers,
        )
        resp = client.get(
            f"/api/discussions/{discussion_id}/messages",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1

    def test_message_wrong_discussion_owner(self, client, auth_headers, second_user_headers, discussion_id):
        resp = client.post(
            "/api/discussions/messages",
            json={
                "discussion_id": discussion_id,
                "round_number": 1,
                "model": "gpt-4",
                "role": "assistant",
                "content": "Should not work",
            },
            headers=second_user_headers,
        )
        assert resp.status_code == 404

    def test_empty_question_rejected(self, client, auth_headers):
        resp = client.post(
            "/api/discussions",
            json={"title": "Empty", "question": ""},
            headers=auth_headers,
        )
        assert resp.status_code == 422
