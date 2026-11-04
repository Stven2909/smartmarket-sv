"""HU-27: bound public Streamlit usage without throttling Laravel."""

import asyncio
from types import SimpleNamespace

import httpx
import pytest

from app.main import app
from app.security import streamlit_rate_limit as limiter


def send(path: str, key: str | None = None) -> httpx.Response:
    async def execute():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            headers = {"X-API-Key": key} if key else {}
            return await client.get(path, headers=headers)

    return asyncio.run(execute())


@pytest.fixture(autouse=True)
def clean_budget():
    limiter.reset_streamlit_rate_limit_for_tests()
    yield
    limiter.reset_streamlit_rate_limit_for_tests()


@pytest.fixture
def separate_keys(monkeypatch):
    monkeypatch.setenv("SMARTMARKET_ENV", "production")
    monkeypatch.setenv("SMARTMARKET_API_KEY", "laravel-key")
    monkeypatch.setenv("SMARTMARKET_API_KEY_STREAMLIT", "streamlit-key")
    monkeypatch.delenv("SMARTMARKET_API_KEY_PREVIOUS", raising=False)
    monkeypatch.setenv("SMARTMARKET_STREAMLIT_RATE_LIMIT_PER_MINUTE", "2")


def test_public_streamlit_has_small_budget_but_laravel_remains_available(separate_keys):
    assert send("/api/v1/knowledge", "streamlit-key").status_code == 200
    assert send("/api/v1/knowledge", "streamlit-key").status_code == 200
    limited = send("/api/v1/knowledge", "streamlit-key")
    assert limited.status_code == 429
    assert limited.json()["detail"].startswith("La demo ha superado")
    assert limited.headers["retry-after"] == "60"
    assert limited.headers["cache-control"] == "no-store"
    assert limited.headers["x-frame-options"] == "DENY"
    assert "streamlit-key" not in limited.text

    for _ in range(4):
        assert send("/api/v1/knowledge", "laravel-key").status_code == 200
    assert send("/api/v1/knowledge").status_code == 401


def test_window_reopens_without_background_tasks(separate_keys, monkeypatch):
    clock = {"now": 10.0}
    monkeypatch.setattr(
        limiter, "time", SimpleNamespace(monotonic=lambda: clock["now"])
    )
    assert send("/api/v1/knowledge", "streamlit-key").status_code == 200
    assert send("/api/v1/knowledge", "streamlit-key").status_code == 200
    clock["now"] += 15
    limited = send("/api/v1/knowledge", "streamlit-key")
    assert limited.status_code == 429
    assert limited.headers["retry-after"] == "45"
    clock["now"] += 46
    assert send("/api/v1/knowledge", "streamlit-key").status_code == 200


def test_existing_same_secret_configuration_remains_compatible(monkeypatch):
    monkeypatch.setenv("SMARTMARKET_ENV", "production")
    monkeypatch.setenv("SMARTMARKET_API_KEY", "shared-secret")
    monkeypatch.setenv("SMARTMARKET_API_KEY_STREAMLIT", "shared-secret")
    monkeypatch.setenv("SMARTMARKET_STREAMLIT_RATE_LIMIT_PER_MINUTE", "1")
    for _ in range(3):
        assert send("/api/v1/knowledge", "shared-secret").status_code == 200


def test_malformed_or_out_of_range_rpm_falls_back_to_safe_default(monkeypatch):
    for value in ("bogus", "0", "-10", "601", "10000000000000000000000000000000"):
        monkeypatch.setenv("SMARTMARKET_STREAMLIT_RATE_LIMIT_PER_MINUTE", value)
        assert limiter.configured_streamlit_rate_limit() == 60
    monkeypatch.setenv("SMARTMARKET_STREAMLIT_RATE_LIMIT_PER_MINUTE", "120")
    assert limiter.configured_streamlit_rate_limit() == 120


def test_limiter_never_retains_more_than_configured_number_of_timestamps(
    separate_keys,
):
    for _ in range(10):
        limiter.streamlit_rate_limit_retry_after()
    assert len(limiter._requests) == 2
