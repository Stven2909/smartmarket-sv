"""HU-26: fail-closed Render, independent keys, and bounded request bodies."""

import asyncio
import os
import subprocess
import sys

import httpx
import pytest

from app.main import app
from app.security.request_size import MAX_API_REQUEST_BYTES, RequestBodySizeLimitMiddleware

FACTS = {
    "request_id": "hu26-001",
    "alternativa_id": "store-1",
    "costo_total": 32.0,
    "presupuesto": 40.0,
    "ahorro": 4.0,
    "distancia_km": 2.0,
    "distancia_adicional_km": 0.5,
    "tiempo_estimado_min": 10.0,
    "productos_disponibles": 5,
    "productos_totales": 5,
    "productos_esenciales_disponibles": 3,
    "productos_esenciales_totales": 3,
    "numero_supermercados": 1,
    "promociones_aplicables": False,
}


def send(method, path, **kwargs):
    async def call():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            return await client.request(method, path, **kwargs)

    return asyncio.run(call())


def test_render_fails_closed_even_if_environment_mistakenly_says_local(monkeypatch):
    monkeypatch.setenv("RENDER", "true")
    monkeypatch.setenv("SMARTMARKET_ENV", "development")
    monkeypatch.delenv("SMARTMARKET_API_KEY", raising=False)
    monkeypatch.delenv("SMARTMARKET_API_KEY_STREAMLIT", raising=False)
    monkeypatch.delenv("SMARTMARKET_API_KEY_PREVIOUS", raising=False)
    assert send("GET", "/api/v1/knowledge").status_code == 503
    assert send("GET", "/health").status_code == 200


def test_render_boot_hides_docs_without_an_explicit_env_or_secret():
    env = dict(os.environ)
    env["RENDER"] = "true"
    env.pop("SMARTMARKET_ENV", None)
    env.pop("SMARTMARKET_API_KEY", None)
    env.pop("SMARTMARKET_API_KEY_STREAMLIT", None)
    env.pop("SMARTMARKET_API_KEY_PREVIOUS", None)
    test = subprocess.run(
        [
            sys.executable, "-c",
            "from app.main import app; "
            "assert app.docs_url is None; "
            "assert app.redoc_url is None; "
            "assert app.openapi_url is None",
        ],
        env=env, capture_output=True, text=True, check=False, timeout=30,
    )
    assert test.returncode == 0, test.stderr


def test_separate_client_secret_can_be_revoked_without_breaking_laravel(monkeypatch):
    monkeypatch.setenv("SMARTMARKET_ENV", "production")
    monkeypatch.setenv("SMARTMARKET_API_KEY", "laravel-secret-test")
    monkeypatch.setenv("SMARTMARKET_API_KEY_STREAMLIT", "streamlit-secret-test")
    monkeypatch.delenv("SMARTMARKET_API_KEY_PREVIOUS", raising=False)

    for secret in ("laravel-secret-test", "streamlit-secret-test"):
        result = send("POST", "/api/v1/recommend", json=FACTS,
                      headers={"X-API-Key": secret})
        assert result.status_code == 200
        assert secret not in result.text

    monkeypatch.delenv("SMARTMARKET_API_KEY_STREAMLIT")
    revoked = send("POST", "/api/v1/recommend", json=FACTS,
                   headers={"X-API-Key": "streamlit-secret-test"})
    assert revoked.status_code == 401
    assert send("POST", "/api/v1/recommend", json=FACTS,
                headers={"X-API-Key": "laravel-secret-test"}).status_code == 200


def test_orphaned_secondary_key_does_not_open_service(monkeypatch):
    monkeypatch.delenv("SMARTMARKET_ENV", raising=False)
    monkeypatch.delenv("SMARTMARKET_API_KEY", raising=False)
    monkeypatch.setenv("SMARTMARKET_API_KEY_STREAMLIT", "orphan-key")
    assert send("GET", "/api/v1/knowledge",
                headers={"X-API-Key": "orphan-key"}).status_code == 503


@pytest.mark.parametrize(
    "path",
    ["/api/v1/recommend", "/api/v1/chat", "/api/v1/evidence-report",
     "/api/v1/rule-regression", "/api/v1/recommend/batch"],
)
def test_oversized_http_request_is_rejected_before_json_parsing(path):
    response = send("POST", path, content=b"x" * (MAX_API_REQUEST_BYTES + 1),
                    headers={"Content-Type": "application/json"})
    assert response.status_code == 413
    assert response.headers["cache-control"] == "no-store"
    assert "x" * 100 not in response.text


def test_legitimate_authenticated_request_remains_compatible(monkeypatch):
    monkeypatch.setenv("SMARTMARKET_ENV", "production")
    monkeypatch.setenv("SMARTMARKET_API_KEY", "laravel-secret-test")
    result = send("POST", "/api/v1/recommend", json=FACTS,
                  headers={"X-API-Key": "laravel-secret-test"})
    assert result.status_code == 200, result.text
    assert len(result.json()) == 16
    assert result.headers["cache-control"] == "no-store"
    assert result.headers["x-frame-options"] == "DENY"
    assert result.headers["referrer-policy"] == "no-referrer"
    assert "access-control-allow-origin" not in result.headers


def test_unauthorized_request_returns_401_with_security_headers(monkeypatch):
    monkeypatch.setenv("SMARTMARKET_ENV", "production")
    monkeypatch.setenv("SMARTMARKET_API_KEY", "laravel-secret-test")
    response = send("POST", "/api/v1/recommend", json=FACTS)
    assert response.status_code == 401
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"


def test_no_content_length_cannot_bypass_body_cap():
    class Inner:
        def __init__(self):
            self.called = False

        async def __call__(self, scope, receive, send):
            self.called = True

    inner = Inner()
    middleware = RequestBodySizeLimitMiddleware(inner)
    scope = {
        "type": "http", "method": "POST", "path": "/api/v1/recommend",
        "headers": [], "http_version": "1.1",
    }
    messages = [
        {"type": "http.request", "body": b"0" * MAX_API_REQUEST_BYTES,
         "more_body": True},
        {"type": "http.request", "body": b"1", "more_body": False},
    ]
    captured = []

    async def receive():
        return messages.pop(0)

    async def sendmsg(message):
        captured.append(message)

    asyncio.run(middleware(scope, receive, sendmsg))
    assert not inner.called
    assert captured[0]["status"] == 413


def test_small_stream_without_content_length_is_replayed_unchanged():
    seen = []

    async def inner(scope, receive, send):
        msg = await receive()
        seen.append(msg["body"])

    async def receive():
        return {"type": "http.request", "body": b'{"message":"hola"}',
                "more_body": False}

    scope = {"type": "http", "method": "POST", "path": "/api/v1/chat", "headers": []}
    asyncio.run(RequestBodySizeLimitMiddleware(inner)(scope, receive, lambda msg: None))
    assert seen == [b'{"message":"hola"}']
