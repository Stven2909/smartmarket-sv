"""HU-18: simulación HTTP con payloads construidos al estilo de Laravel."""

import asyncio
import json
from pathlib import Path

import httpx

from app.main import app
from app.schemas.recommendation import RecommendationRequest, RecommendationResponse

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "laravel_expert_payloads.json"


def request(method, path, **kwargs):
    async def send():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            return await client.request(method, path, **kwargs)

    return asyncio.run(send())


def data():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_laravel_fixture_is_traceable_and_has_frozen_fourteen_fields():
    fixture = data()
    assert "1cc886ad45a0bfbac156717ffc7ff6e10fbd716d" in fixture["fuente_laravel"]
    assert "ExpertSystemService.php" in fixture["fuente_cliente"]
    keys = set(RecommendationRequest.model_fields)
    assert len(keys) == 14
    for case in fixture["validos"] + fixture["invalidos"]:
        assert set(case["hechos"]) == keys
        assert case["hechos"]["request_id"].startswith("lista-")


def test_laravel_style_payloads_return_expected_expert_results():
    for case in data()["validos"]:
        response = request("POST", "/api/v1/recommend", json=case["hechos"])
        assert response.status_code == 200, (case["nombre"], response.text)
        result = RecommendationResponse.model_validate(response.json())
        assert result.request_id == case["hechos"]["request_id"]
        assert result.nivel_recomendacion == case["esperado"]["nivel"]
        assert result.winning_rule == case["esperado"]["regla"]
        assert len(result.trace) == 11


def test_laravel_batch_style_correlation_by_request_id_is_unambiguous():
    responses = {}
    for case in data()["validos"]:
        response = request("POST", "/api/v1/recommend", json=case["hechos"])
        assert response.status_code == 200
        responses[case["hechos"]["request_id"]] = response.json()
    assert len(responses) == len(data()["validos"])
    assert all(item["request_id"] == request_id for request_id, item in responses.items())


def test_invalid_or_incomplete_payloads_are_explicitly_rejected():
    for case in data()["invalidos"]:
        result = request("POST", "/api/v1/recommend", json=case["hechos"])
        assert result.status_code == 422, case["nombre"]


def test_api_key_uses_same_laravel_header_and_never_echoes_it(monkeypatch):
    monkeypatch.setenv("SMARTMARKET_API_KEY", "laravel-fake-secret")
    payload = data()["validos"][0]["hechos"]
    assert request("POST", "/api/v1/recommend", json=payload).status_code == 401
    answer = request(
        "POST", "/api/v1/recommend",
        json=payload,
        headers={"X-API-Key": "laravel-fake-secret"},
    )
    assert answer.status_code == 200
    assert "laravel-fake-secret" not in answer.text


def test_openapi_consumer_contract_has_not_changed():
    spec = request("GET", "/openapi.json").json()
    definitions = spec["components"]["schemas"]
    assert len(definitions["RecommendationRequest"]["properties"]) == 14
    assert len(definitions["RecommendationResponse"]["properties"]) == 16
