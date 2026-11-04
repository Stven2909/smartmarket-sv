"""HU-24: optional bounded batch inference without changing single recommend."""

import asyncio

import httpx
import pytest

from app.api import recommendation_routes
from app.expert_system.rule_loader import RuleLoaderError
from app.main import app
from app.schemas.batch_recommendation import MAX_BATCH_SIZE
from app.schemas.recommendation import RecommendationRequest, RecommendationResponse

FACTS = {
    "request_id": "batch-one",
    "alternativa_id": "one",
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


def fixture_items():
    return [
        FACTS,
        {
            **FACTS,
            "request_id": "batch-two",
            "alternativa_id": "two",
            "productos_disponibles": 9,
            "productos_esenciales_disponibles": 5,
        },
        {
            **FACTS,
            "request_id": "batch-three",
            "alternativa_id": "three",
            "costo_total": 56.0,
        },
    ]


def test_batch_results_equal_individual_inference_in_same_order():
    inputs = fixture_items()
    response = send(
        "POST", "/api/v1/recommend/batch", json={"alternativas": inputs}
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert set(payload) == {"resultados"}
    assert len(payload["resultados"]) == len(inputs)
    assert [value["request_id"] for value in payload["resultados"]] == [
        item["request_id"] for item in inputs
    ]
    for item, returned in zip(inputs, payload["resultados"], strict=True):
        original = send("POST", "/api/v1/recommend", json=item)
        assert original.status_code == 200
        assert returned == original.json()
        assert set(returned) == set(RecommendationResponse.model_fields)

    assert [value["winning_rule"] for value in payload["resultados"]] == [
        "R06", "R02", "R01"
    ]
    assert response.headers["x-expert-rules-sha256"]
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"


def test_one_invalid_item_rejects_entire_batch():
    invalid = fixture_items()
    invalid[1] = {**invalid[1], "presupuesto": 0}
    response = send("POST", "/api/v1/recommend/batch", json={"alternativas": invalid})
    assert response.status_code == 422
    assert "resultados" not in response.json()


@pytest.mark.parametrize("invalid", [[], [{}], [{"x": "y"}]])
def test_batch_rejects_empty_and_incomplete_arrays(invalid):
    response = send("POST", "/api/v1/recommend/batch", json={"alternativas": invalid})
    assert response.status_code == 422


def test_duplicate_request_ids_are_rejected_without_silent_overwrite():
    same = [FACTS, {**FACTS, "alternativa_id": "another-store"}]
    response = send("POST", "/api/v1/recommend/batch", json={"alternativas": same})
    assert response.status_code == 422
    assert "request_id" in response.text


def test_batch_size_limit_prevents_unbounded_work():
    values = [
        {**FACTS, "request_id": f"unique-{i}", "alternativa_id": f"store-{i}"}
        for i in range(MAX_BATCH_SIZE + 1)
    ]
    response = send("POST", "/api/v1/recommend/batch", json={"alternativas": values})
    assert response.status_code == 422


def test_one_item_is_allowed_and_retains_fourteen_input_fields():
    assert len(RecommendationRequest.model_fields) == 14
    response = send(
        "POST", "/api/v1/recommend/batch", json={"alternativas": [FACTS]}
    )
    assert response.status_code == 200
    assert len(response.json()["resultados"]) == 1


def test_batch_is_secured_by_the_same_x_api_key(monkeypatch):
    monkeypatch.setenv("SMARTMARKET_ENV", "production")
    monkeypatch.setenv("SMARTMARKET_API_KEY", "protected-test-key")
    anonymous = send(
        "POST", "/api/v1/recommend/batch",
        json={"alternativas": [FACTS]},
    )
    assert anonymous.status_code == 401
    authorized = send(
        "POST", "/api/v1/recommend/batch",
        json={"alternativas": [FACTS]},
        headers={"X-API-Key": "protected-test-key"},
    )
    assert authorized.status_code == 200


def test_batch_returns_generic_503_for_rules_unavailable(monkeypatch):
    def broken(_facts):
        raise RuleLoaderError("private/system/path.json")

    monkeypatch.setattr(recommendation_routes, "recommend", broken)
    result = send(
        "POST", "/api/v1/recommend/batch", json={"alternativas": [FACTS]}
    )
    assert result.status_code == 503
    assert "private" not in result.text


def test_batch_rejects_unknown_request_keys():
    response = send(
        "POST", "/api/v1/recommend/batch",
        json={"alternativas": [FACTS], "rank_supermarkets": True},
    )
    assert response.status_code == 422
