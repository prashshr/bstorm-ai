import pytest
from fastapi.testclient import TestClient


def test_personas_crud_workflow(client: TestClient, auth_headers: dict):
    # 1. Create a custom persona
    create_payload = {
        "name": "Security Auditor",
        "role_description": "OWASP & Vulnerability Expert",
        "system_prompt": "You are a senior security auditor.",
        "model": "openrouter::openai/gpt-4o",
        "avatar": "🛡️",
    }
    resp = client.post("/api/personas", json=create_payload, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    persona_id = data["id"]
    assert data["name"] == "Security Auditor"
    assert data["avatar"] == "🛡️"

    # 2. List personas
    resp = client.get("/api/personas", headers=auth_headers)
    assert resp.status_code == 200
    personas = resp.json()
    assert len(personas) >= 1
    assert any(p["id"] == persona_id for p in personas)

    # 3. Update persona
    update_payload = {"name": "Senior Security Lead", "avatar": "🔒"}
    resp = client.put(f"/api/personas/{persona_id}", json=update_payload, headers=auth_headers)
    assert resp.status_code == 200
    updated = resp.json()
    assert updated["name"] == "Senior Security Lead"
    assert updated["avatar"] == "🔒"

    # 4. Delete persona
    resp = client.delete(f"/api/personas/{persona_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["deleted"] is True
