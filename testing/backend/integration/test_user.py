import pytest
from fastapi.testclient import TestClient


def test_user_settings_workflow(client: TestClient, auth_headers: dict):
    # 1. Get initial settings (should be empty object)
    resp = client.get("/api/user/settings", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "settings" in data

    # 2. Update user settings
    new_settings = {
        "defaultRagMode": "model-self",
        "defaultConsensusEnabled": True,
        "defaultResponseFormat": "compact",
        "defaultSummaryFormat": "compact",
        "themeAccent": "#2b7a4d",
        "autoMinimizeComposer": False,
    }
    resp = client.put("/api/user/settings", json={"settings": new_settings}, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    updated = resp.json()["settings"]
    assert updated["defaultRagMode"] == "model-self"
    assert updated["defaultConsensusEnabled"] is True
    assert updated["themeAccent"] == "#2b7a4d"
    assert updated["autoMinimizeComposer"] is False

    # 3. Retrieve updated settings
    resp = client.get("/api/user/settings", headers=auth_headers)
    assert resp.status_code == 200
    retrieved = resp.json()["settings"]
    assert retrieved["themeAccent"] == "#2b7a4d"
    assert retrieved["defaultResponseFormat"] == "compact"


def test_user_change_password_invalid(client: TestClient, auth_headers: dict):
    # Test invalid current password
    resp = client.post(
        "/api/user/change-password",
        json={"current_password": "WrongPassword123!", "new_password": "NewSecretPassword123!"},
        headers=auth_headers,
    )
    assert resp.status_code == 400
    assert "incorrect" in resp.json()["detail"].lower()
