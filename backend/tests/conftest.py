import os
import sys
import tempfile
import base64

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.db.session import Base, get_db
from app.main import app
from app.core.config import settings
from app.core.limiter import limiter


TEST_DB_FD, TEST_DB_PATH = tempfile.mkstemp(suffix=".db")


@pytest.fixture(scope="session")
def test_db_url():
    return f"sqlite:///{TEST_DB_PATH}"


@pytest.fixture(scope="session")
def engine(test_db_url):
    e = create_engine(test_db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=e)
    yield e
    Base.metadata.drop_all(bind=e)


@pytest.fixture(scope="function")
def db_session(engine):
    TestingSession = sessionmaker(bind=engine)
    session = TestingSession()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture(scope="function")
def client(engine):
    TestingSession = sessionmaker(bind=engine)

    def override_get_db():
        session = TestingSession()
        try:
            yield session
        finally:
            session.rollback()
            session.close()

    limiter.enabled = False
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    limiter.enabled = True


@pytest.fixture(scope="function")
def auth_headers(client, request):
    uid = id(request.node) % 100000
    resp = client.post(
        "/api/auth/register",
        json={"email": f"testuser{uid}@test.com", "password": "testpass123"},
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def second_user_headers(client, request):
    uid = id(request.node) % 100000
    resp = client.post(
        "/api/auth/register",
        json={"email": f"user2{uid}@test.com", "password": "pass2word456"},
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def discussion_id(client, auth_headers):
    resp = client.post(
        "/api/discussions",
        json={"title": "Test Discussion", "question": "What is AI?", "use_rag": False},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    return resp.json()["id"]


@pytest.fixture
def provider_payload():
    return {
        "provider": "openai",
        "api_key": "sk-test-key-12345",
        "endpoint": "https://api.openai.com/v1",
    }


@pytest.fixture(autouse=True)
def isolate_env():
    settings.tavily_api_key = ""
    settings.searxng_url = "http://localhost:9999"
    yield


@pytest.fixture
def valid_uek():
    return base64.urlsafe_b64encode(b"a" * 32).decode()


def cleanup():
    os.close(TEST_DB_FD)
    os.unlink(TEST_DB_PATH)


def pytest_sessionfinish():
    cleanup()

