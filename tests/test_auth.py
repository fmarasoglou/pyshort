"""Auth, redirect-safety and keyword tests for the pyshort service.

The app resolves its database URL and calls ``db.create_all()`` at import time,
so the suite points it at a throwaway SQLite file (``PYSHORT_DATABASE_URL``)
before importing, and swaps the module-level Redis client for a dict-backed
stand-in. No Postgres, Redis or network is required.

Run from the repo root:  pip install -r requirements.txt pytest && pytest -q
"""
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["PYSHORT_DATABASE_URL"] = (
    "sqlite:///" + os.path.join(tempfile.mkdtemp(), "test.db")
)
os.environ["PYSHORT_SERVICE_TOKEN"] = "test-token"

import app as app_module  # noqa: E402  (env must be set before import)

TOKEN = {"X-Service-Token": "test-token"}


class FakeRedis:
    """Minimal stand-in for redis.Redis: the cache is a plain dict."""

    def __init__(self):
        self.store = {}

    def get(self, key):
        return self.store.get(key)

    def set(self, key, value, ex=None):
        self.store[key] = value
        return True

    def delete(self, *keys):
        for key in keys:
            self.store.pop(key, None)


@pytest.fixture(autouse=True)
def clean_state(monkeypatch):
    monkeypatch.setattr(app_module, "redis_db1", FakeRedis())
    with app_module.app.app_context():
        app_module.db.drop_all()
        app_module.db.create_all()
    yield


@pytest.fixture
def client():
    app_module.app.config.update(TESTING=True)
    return app_module.app.test_client()


def create(client, long_url="https://example.com/a"):
    response = client.post(
        "/create_url", json={"long_url": long_url, "title": "t"}, headers=TOKEN
    )
    assert response.status_code == 201
    return response.get_json()["data"]["keyword"]


@pytest.mark.parametrize(
    "method,path",
    [
        ("post", "/create_url"),
        ("get", "/get_urls"),
        ("put", "/update_url/somekw"),
        ("get", "/url/somekw"),
        ("get", "/healthz"),
    ],
)
def test_management_routes_401_without_token(client, method, path):
    response = getattr(client, method)(path)
    assert response.status_code == 401
    assert response.get_json() == {"error": "unauthorized"}


@pytest.mark.parametrize(
    "method,path",
    [
        ("post", "/create_url"),
        ("get", "/get_urls"),
        ("put", "/update_url/somekw"),
        ("get", "/url/somekw"),
        ("get", "/healthz"),
    ],
)
def test_management_routes_401_with_wrong_token(client, method, path):
    response = getattr(client, method)(path, headers={"X-Service-Token": "nope"})
    assert response.status_code == 401


def test_token_unset_fails_closed(client, monkeypatch):
    monkeypatch.delenv("PYSHORT_SERVICE_TOKEN")
    assert client.get("/get_urls").status_code == 401
    # An empty token is not a token either.
    monkeypatch.setenv("PYSHORT_SERVICE_TOKEN", "")
    assert client.get("/get_urls").status_code == 401


def test_healthz_204_with_token(client):
    assert client.get("/healthz", headers=TOKEN).status_code == 204


def test_authorized_roundtrip(client):
    keyword = create(client)
    assert 6 <= len(keyword) <= 8

    listed = client.get("/get_urls", headers=TOKEN)
    assert listed.status_code == 200
    assert [row["keyword"] for row in listed.get_json()] == [keyword]

    detail = client.get(f"/url/{keyword}", headers=TOKEN)
    assert detail.status_code == 200
    assert detail.get_json()["long_url"] == "https://example.com/a"

    assert client.get(f"/url/{keyword}").status_code == 401

    updated = client.put(
        f"/update_url/{keyword}",
        json={"long_url": "https://example.com/b"},
        headers=TOKEN,
    )
    assert updated.status_code == 201
    assert updated.get_json()["data"]["long_url"] == "https://example.com/b"


def test_docs_requires_token(client):
    assert client.get("/api/docs").status_code == 401
    assert client.get("/api/docs", headers=TOKEN).status_code == 200


def test_redirect_public_and_truncates_long_user_agent(client):
    keyword = create(client)
    response = client.get(
        f"/r/{keyword}",
        headers={
            "User-Agent": "u" * 400,
            "Referer": "https://referrer.example/" + "r" * 400,
        },
    )
    assert response.status_code == 302
    assert response.headers["Location"] == "https://example.com/a"

    with app_module.app.app_context():
        log = app_module.Logs.query.filter_by(keyword=keyword).one()
        assert len(log.user_agent) == 255
        assert len(log.referrer) == 200
        assert app_module.Url.query.filter_by(keyword=keyword).one().count == 1


def test_redirect_survives_logging_failure(client, monkeypatch):
    keyword = create(client)

    class Boom:
        def __init__(self, **kwargs):
            raise RuntimeError("log write failed")

    monkeypatch.setattr(app_module, "Logs", Boom)
    response = client.get(f"/r/{keyword}", headers={"User-Agent": "x" * 400})
    assert response.status_code == 302
    assert response.headers["Location"] == "https://example.com/a"
    # The link was cached despite the failed write.
    assert app_module.redis_db1.get(f"/r/{keyword}") == '"https://example.com/a"'


def test_cache_write_failure_is_logged_not_claimed(client, monkeypatch, caplog):
    keyword = create(client)

    class Boom:
        def set(self, *args, **kwargs):
            raise RuntimeError("redis down")

    monkeypatch.setattr(app_module, "redis_db1", Boom())
    with caplog.at_level("INFO"):
        response = client.get(f"/r/{keyword}")
    assert response.status_code == 302
    assert "cache set failed" in caplog.text
    assert f"cache set for /r/{keyword}" not in caplog.text
