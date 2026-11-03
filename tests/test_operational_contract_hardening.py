"""HU-20/HU-21: service-owned safeguards, independent of Laravel writes."""

import asyncio

import httpx
import pytest
from pydantic import ValidationError

from app.api import health_routes
from app.main import app
from app.schemas.recommendation import RecommendationRequest
from app.expert_system.rule_loader import RuleLoaderError
from scripts.check_laravel_contract import payload_fields_from_php, validate_php_contract

VALID = {
    "request_id": "lista-1-sucursal-2",
    "alternativa_id": "sucursal-2",
    "costo_total": 30.0,
    "presupuesto": 40.0,
    "ahorro": 3.0,
    "distancia_km": 2.0,
    "distancia_adicional_km": 0.5,
    "tiempo_estimado_min": 10.0,
    "productos_disponibles": 6,
    "productos_totales": 6,
    "productos_esenciales_disponibles": 4,
    "productos_esenciales_totales": 4,
    "numero_supermercados": 1,
    "promociones_aplicables": False,
}


def send(method: str, path: str, **kwargs) -> httpx.Response:
    async def make_request():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            return await client.request(method, path, **kwargs)

    return asyncio.run(make_request())


@pytest.mark.parametrize(
    "changes",
    [
        {"costo_total": 1e308, "presupuesto": 1e-308},
        {"costo_total": 1e308, "presupuesto": 1.0},
        {"costo_total": 1e100, "presupuesto": 1e-300},
    ],
)
def test_extreme_finite_numbers_do_not_break_inference(changes):
    with pytest.raises(ValidationError, match="cálculos fuera de rango"):
        RecommendationRequest.model_validate({**VALID, **changes})
    response = send("POST", "/api/v1/recommend", json={**VALID, **changes})
    assert response.status_code == 422


@pytest.mark.parametrize("field", ["request_id", "alternativa_id"])
def test_rejects_unbounded_identifiers(field):
    response = send("POST", "/api/v1/recommend", json={**VALID, field: "x" * 257})
    assert response.status_code == 422


def test_normal_laravel_request_keeps_exact_contract_and_output():
    response = send("POST", "/api/v1/recommend", json=VALID)
    assert response.status_code == 200
    assert response.json()["request_id"] == VALID["request_id"]
    assert len(RecommendationRequest.model_fields) == 14
    assert response.json()["winning_rule"] == "R06"


def test_readiness_checks_rules_but_health_remains_lightweight():
    assert send("GET", "/health").json()["status"] == "ok"
    assert send("GET", "/ready").json()["status"] == "ready"


def test_readiness_reports_unavailable_rules_without_leaking_details(monkeypatch):
    def fail():
        raise RuleLoaderError("sensitive path: /runtime/private/rules.json")

    monkeypatch.setattr(health_routes, "load_rules", fail)
    response = send("GET", "/ready")
    assert response.status_code == 503
    assert "sensitive" not in response.text
    assert send("GET", "/health").status_code == 200


def test_production_without_configured_api_key_fails_closed(monkeypatch):
    monkeypatch.setenv("SMARTMARKET_ENV", "production")
    monkeypatch.delenv("SMARTMARKET_API_KEY", raising=False)
    assert send("POST", "/api/v1/recommend", json=VALID).status_code == 503
    assert send("POST", "/api/v1/chat", json={"message": "Hola"}).status_code == 503
    assert send("GET", "/health").status_code == 200

    monkeypatch.setenv("SMARTMARKET_API_KEY", "safe-test-key")
    assert send("POST", "/api/v1/recommend", json=VALID).status_code == 401
    response = send(
        "POST", "/api/v1/recommend", json=VALID,
        headers={"X-API-Key": "safe-test-key"},
    )
    assert response.status_code == 200


def test_development_without_configured_api_key_remains_compatible(monkeypatch):
    monkeypatch.delenv("SMARTMARKET_ENV", raising=False)
    monkeypatch.delenv("SMARTMARKET_API_KEY", raising=False)
    assert send("POST", "/api/v1/recommend", json=VALID).status_code == 200


def php_payload(fields):
    keys = "\n".join(f"            '{field}' => 1," for field in fields)
    return (
        "<?php\nclass OptimizationService {\n"
        "    public function construirPayload() {\n"
        "        return [\n" + keys + "\n        ];\n"
        "    }\n}\n"
    )


PHP_CLIENT = (
    "$url = 'https://example.test/api/v1/recommend';\n"
    "$requestId = $payload['request_id'] ?? 'unknown';\n"
    "$response = $this->httpClient()->post($url, $payload);\n"
    "$client = $client->withHeaders(['X-API-Key' => $apiKey]);\n"
)


def test_read_only_contract_checker_accepts_current_fields():
    fields = list(RecommendationRequest.model_fields)
    producer = php_payload(fields)
    assert payload_fields_from_php(producer) == fields
    validate_php_contract(producer, PHP_CLIENT)


@pytest.mark.parametrize("change", ["remove", "extra", "duplicate"])
def test_read_only_contract_checker_detects_drift(change):
    fields = list(RecommendationRequest.model_fields)
    if change == "remove":
        fields.pop()
    elif change == "extra":
        fields.append("score")
    else:
        fields.append(fields[0])

    with pytest.raises(ValueError):
        validate_php_contract(php_payload(fields), PHP_CLIENT)


def test_read_only_contract_checker_detects_endpoint_and_key_drift():
    producer = php_payload(list(RecommendationRequest.model_fields))
    with pytest.raises(ValueError, match="endpoint|envía"):
        validate_php_contract(producer, PHP_CLIENT.replace("/api/v1/recommend", "/api/v2/recommend"))
    with pytest.raises(ValueError, match="X-API-Key"):
        validate_php_contract(producer, PHP_CLIENT.replace("X-API-Key", "X-Legacy-Key"))
