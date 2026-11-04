"""HU-23: Laravel-to-Python authentication and secure response headers."""

import asyncio
import os
import subprocess
import sys

import httpx
import pytest

from app.main import app
from app.schemas.recommendation import RecommendationResponse

VALID = {
    "request_id": "seguridad-001",
    "alternativa_id": "supermercado-1",
    "costo_total": 42.5,
    "presupuesto": 50.0,
    "ahorro": 11.25,
    "distancia_km": 2.3,
    "distancia_adicional_km": 0.8,
    "tiempo_estimado_min": 12.0,
    "productos_disponibles": 10,
    "productos_totales": 10,
    "productos_esenciales_disponibles": 6,
    "productos_esenciales_totales": 6,
    "numero_supermercados": 1,
    "promociones_aplicables": True,
}


def send(method: str, path: str, **kwargs) -> httpx.Response:
    async def execute():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            return await client.request(method, path, **kwargs)

    return asyncio.run(execute())


@pytest.fixture
def production(monkeypatch):
    monkeypatch.setenv("SMARTMARKET_ENV", "production")
    monkeypatch.setenv("SMARTMARKET_API_KEY", "current-secret-for-tests")
    monkeypatch.delenv("SMARTMARKET_API_KEY_PREVIOUS", raising=False)


@pytest.mark.parametrize(
    "method,path",
    [
        ("POST", "/api/v1/recommend"),
        ("POST", "/api/v1/chat"),
        ("POST", "/api/v1/compare"),
        ("POST", "/api/v1/sensitivity"),
        ("POST", "/api/v1/diagnosis"),
        ("POST", "/api/v1/rule-regression"),
        ("POST", "/api/v1/evidence-report"),
        ("GET", "/api/v1/knowledge"),
        ("GET", "/api/v1/rule-audit"),
    ],
)
def test_every_business_route_blocks_anonymous_requests(production, method, path):
    response = send(method, path)
    assert response.status_code == 401
    assert response.json()["detail"] == "API key inválida o ausente."
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "X-API-Key" in response.headers["vary"]
    assert "current-secret-for-tests" not in response.text


def test_valid_service_key_retains_original_json_contract(production):
    response = send(
        "POST",
        "/api/v1/recommend",
        json=VALID,
        headers={"X-API-Key": "current-secret-for-tests"},
    )
    assert response.status_code == 200
    assert response.json()["request_id"] == VALID["request_id"]
    assert set(response.json()) == set(RecommendationResponse.model_fields)
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "X-API-Key" in response.headers["vary"]
    assert "current-secret-for-tests" not in response.text


def test_key_rotation_allows_only_current_and_temporary_previous(production, monkeypatch):
    monkeypatch.setenv("SMARTMARKET_API_KEY_PREVIOUS", "old-secret-for-tests")

    for secret in ("current-secret-for-tests", "old-secret-for-tests"):
        response = send(
            "POST", "/api/v1/recommend",
            json=VALID, headers={"X-API-Key": secret},
        )
        assert response.status_code == 200
        assert secret not in response.text

    bad = send(
        "POST", "/api/v1/recommend",
        json=VALID, headers={"X-API-Key": "unrecognized-secret"},
    )
    assert bad.status_code == 401

    monkeypatch.delenv("SMARTMARKET_API_KEY_PREVIOUS")
    revoked = send(
        "POST", "/api/v1/recommend",
        json=VALID, headers={"X-API-Key": "old-secret-for-tests"},
    )
    assert revoked.status_code == 401


def test_previous_key_alone_cannot_enable_service(monkeypatch):
    monkeypatch.delenv("SMARTMARKET_ENV", raising=False)
    monkeypatch.delenv("SMARTMARKET_API_KEY", raising=False)
    monkeypatch.setenv("SMARTMARKET_API_KEY_PREVIOUS", "old-only")
    rejected = send(
        "POST", "/api/v1/recommend",
        json=VALID, headers={"X-API-Key": "old-only"},
    )
    assert rejected.status_code == 503
    assert "old-only" not in rejected.text


def test_production_without_primary_key_is_closed(monkeypatch):
    monkeypatch.setenv("SMARTMARKET_ENV", "production")
    monkeypatch.delenv("SMARTMARKET_API_KEY", raising=False)
    monkeypatch.delenv("SMARTMARKET_API_KEY_PREVIOUS", raising=False)
    assert send("POST", "/api/v1/recommend", json=VALID).status_code == 503
    assert send("GET", "/api/v1/knowledge").status_code == 503


def test_invalid_payload_is_not_cached_even_with_valid_key(production):
    response = send(
        "POST", "/api/v1/recommend",
        json={**VALID, "presupuesto": 0},
        headers={"X-API-Key": "current-secret-for-tests"},
    )
    assert response.status_code == 422
    assert response.headers["cache-control"] == "no-store"


def test_public_health_and_readiness_do_not_require_service_secret(production):
    assert send("GET", "/health").status_code == 200
    assert send("GET", "/ready").status_code == 200


def test_production_boot_hides_interactive_docs_and_schema():
    env = dict(os.environ)
    env["SMARTMARKET_ENV"] = "production"
    env["SMARTMARKET_API_KEY"] = "service-secret-for-tests"
    process = subprocess.run(
        [
            sys.executable,
            "-c",
            "from app.main import app; "
            "assert app.docs_url is None; "
            "assert app.redoc_url is None; "
            "assert app.openapi_url is None",
        ],
        env=env, check=False, capture_output=True, text=True, timeout=30,
    )
    assert process.returncode == 0, process.stderr
