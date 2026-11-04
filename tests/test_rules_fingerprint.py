"""HU-22: stable rule identity and controlled failures, without API JSON drift."""

import asyncio
import re

import httpx
from pydantic import ValidationError

from app.api import recommendation_routes
from app.expert_system.rule_loader import RuleLoaderError, load_rules
from app.expert_system.rules_fingerprint import (
    current_rules_fingerprint,
    fingerprint_for_rules,
)
from app.main import app
from app.schemas.recommendation import RecommendationRequest, RecommendationResponse

PAYLOAD = {
    "request_id": "lista-2-sucursal-9",
    "alternativa_id": "sucursal-9",
    "costo_total": 42.50,
    "presupuesto": 50.0,
    "ahorro": 11.25,
    "distancia_km": 2.3,
    "distancia_adicional_km": 0.8,
    "tiempo_estimado_min": 12,
    "productos_disponibles": 10,
    "productos_totales": 10,
    "productos_esenciales_disponibles": 6,
    "productos_esenciales_totales": 6,
    "numero_supermercados": 1,
    "promociones_aplicables": True,
}


def request(method: str, path: str, **kwargs) -> httpx.Response:
    async def invoke():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            return await client.request(method, path, **kwargs)

    return asyncio.run(invoke())


def test_production_fingerprint_is_stable_and_valid_sha256():
    fingerprint = current_rules_fingerprint()
    assert re.fullmatch(r"[0-9a-f]{64}", fingerprint)
    assert fingerprint == current_rules_fingerprint()
    assert fingerprint == fingerprint_for_rules(load_rules())


def test_fingerprint_ignores_json_order_but_tracks_rule_semantics():
    rules = load_rules()
    before = fingerprint_for_rules(rules)
    assert fingerprint_for_rules(list(reversed(rules))) == before
    changed = [rule.model_copy(deep=True) for rule in rules]
    changed[0].priority += 10
    assert fingerprint_for_rules(changed) != before


def test_recommendation_keeps_body_contract_and_exposes_fingerprint_header():
    result = request("POST", "/api/v1/recommend", json=PAYLOAD)
    assert result.status_code == 200
    assert result.headers["X-Expert-Rules-SHA256"] == current_rules_fingerprint()
    parsed = RecommendationResponse.model_validate(result.json())
    assert set(result.json()) == set(RecommendationResponse.model_fields)
    assert len(result.json()) == 16
    assert parsed.request_id == PAYLOAD["request_id"]
    assert parsed.winning_rule == "R06"
    assert parsed.version_reglas == "1.3.1"


def test_ready_and_knowledge_expose_same_deployment_fingerprint():
    ready = request("GET", "/ready")
    knowledge = request("GET", "/api/v1/knowledge")
    assert ready.status_code == 200
    assert knowledge.status_code == 200
    assert ready.headers["X-Expert-Rules-SHA256"] == current_rules_fingerprint()
    assert knowledge.headers["X-Expert-Rules-SHA256"] == current_rules_fingerprint()
    assert ready.json() == {
        "status": "ready",
        "service": "smartmarket-expert-service",
    }
    assert "rules" in knowledge.json()
    assert "rules_fingerprint" not in knowledge.json()


def test_invalid_payload_does_not_claim_a_rule_fingerprint():
    invalid = request("POST", "/api/v1/recommend", json={**PAYLOAD, "presupuesto": 0})
    assert invalid.status_code == 422
    assert "X-Expert-Rules-SHA256" not in invalid.headers


def test_unavailable_rule_base_returns_503_without_exposing_internal_paths(monkeypatch):
    def broken(_request):
        raise RuleLoaderError("private/path/with/sensitive/details.json")

    monkeypatch.setattr(recommendation_routes, "recommend", broken)
    failure = request("POST", "/api/v1/recommend", json=PAYLOAD)
    assert failure.status_code == 503
    assert "sensitive" not in failure.text
    assert "X-Expert-Rules-SHA256" not in failure.headers


def test_original_fourteen_fact_keys_and_validation_are_untouched():
    assert len(RecommendationRequest.model_fields) == 14
    valid = RecommendationRequest.model_validate(PAYLOAD)
    assert valid.request_id == PAYLOAD["request_id"]
    try:
        RecommendationRequest.model_validate({**PAYLOAD, "numero_supermercados": 0})
    except ValidationError:
        pass
    else:
        raise AssertionError("Inconsistent inputs must still be rejected")
