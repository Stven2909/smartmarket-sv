"""Pruebas de humo de Python/FastAPI y Streamlit, sin depender de Laravel."""

import asyncio
from pathlib import Path

import httpx
import pytest
from streamlit.testing.v1 import AppTest

from app.main import app
from app.schemas.recommendation import RecommendationRequest, RecommendationResponse
from demo.streamlit_app import call_recommendation_api, validate_payload

BASE = {
    "request_id": "smoke-001",
    "alternativa_id": "sucursal-1",
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

REQUEST_KEYS = set(BASE)
RESPONSE_KEYS = {
    "request_id",
    "nivel_recomendacion",
    "accion_sugerida",
    "explicacion",
    "reglas_activadas",
    "prioridad_aplicada",
    "hechos_derivados",
    "version_reglas",
    "version_contrato",
    "winning_rule",
    "losing_rules",
    "trace",
    "indice_conveniencia",
    "clasificacion_conveniencia",
    "componentes_conveniencia",
    "pesos_conveniencia",
}


def payload(**changes):
    return {**BASE, **changes}


def api_request(method, path, **kwargs):
    """Llama a la aplicación FastAPI real en memoria, sin levantar un servidor."""

    async def send():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            return await client.request(method, path, **kwargs)

    return asyncio.run(send())


def test_openapi_request_and_response_keep_the_same_fields():
    assert set(RecommendationRequest.model_fields) == REQUEST_KEYS
    assert set(RecommendationResponse.model_fields) == RESPONSE_KEYS

    result = api_request("GET", "/openapi.json")
    assert result.status_code == 200
    schemas = result.json()["components"]["schemas"]
    assert set(schemas["RecommendationRequest"]["properties"]) == REQUEST_KEYS
    assert set(schemas["RecommendationRequest"]["required"]) == REQUEST_KEYS
    assert set(schemas["RecommendationResponse"]["properties"]) == RESPONSE_KEYS
    assert schemas["RecommendationRequest"]["properties"][
        "productos_esenciales_totales"
    ]["minimum"] == 0


def test_health_endpoint_works_without_laravel():
    response = api_request("GET", "/health")
    assert response.status_code == 200


@pytest.mark.parametrize(
    ("changes", "expected_rule", "expected_level"),
    [
        ({}, "R06", "EXCELENTE"),
        ({"costo_total": 56.0}, "R01", "NO_RECOMENDABLE"),
        (
            {"productos_disponibles": 9, "productos_esenciales_disponibles": 5},
            "R02",
            "NO_RECOMENDABLE",
        ),
        (
            {"productos_disponibles": 9},
            "R06",
            "EXCELENTE",
        ),
        (
            {
                "productos_esenciales_totales": 0,
                "productos_esenciales_disponibles": 0,
            },
            "R06",
            "EXCELENTE",
        ),
    ],
)
def test_recommendation_http_is_explainable(changes, expected_rule, expected_level):
    response = api_request("POST", "/api/v1/recommend", json=payload(**changes))
    assert response.status_code == 200
    body = response.json()
    assert set(body) == RESPONSE_KEYS
    assert body["request_id"] == BASE["request_id"]
    assert body["winning_rule"] == expected_rule
    assert body["nivel_recomendacion"] == expected_level
    assert expected_rule in body["reglas_activadas"]
    assert 0 <= body["indice_conveniencia"] <= 100
    assert len(body["trace"]) == 16
    assert any(
        item["rule_id"] == expected_rule and item["activated"]
        for item in body["trace"]
    )
    RecommendationResponse.model_validate(body)


def test_r06_warning_is_visible_in_real_http_response():
    response = api_request(
        "POST", "/api/v1/recommend", json=payload(productos_disponibles=9)
    )
    assert response.status_code == 200
    body = response.json()
    assert body["hechos_derivados"]["todos_productos_disponibles"] is False
    assert "opcionales" in body["accion_sugerida"].lower()
    assert "comprar todo" not in body["accion_sugerida"].lower()


def test_chat_explains_the_exact_recommendation_without_recalculating():
    original = api_request("POST", "/api/v1/recommend", json=payload()).json()
    chat = api_request(
        "POST",
        "/api/v1/chat",
        json={
            "message": "¿Qué regla ganó?",
            "facts": payload(),
            "recommendation": original,
        },
    )
    assert chat.status_code == 200
    assert chat.json()["intent"] == "REGLA_GANADORA"
    assert chat.json()["request_id"] == BASE["request_id"]
    assert original["winning_rule"] in chat.json()["response"]


@pytest.mark.parametrize(
    "changes",
    [
        {"productos_esenciales_totales": 11},
        {"productos_disponibles": 5, "productos_esenciales_disponibles": 6},
        {"productos_disponibles": 10, "productos_esenciales_disponibles": 5},
        {"productos_esenciales_totales": 0, "productos_esenciales_disponibles": 1},
        {"presupuesto": None},
        {"score": 42.0},
    ],
)
def test_bad_payload_is_422_and_streamlit_rejects_bad_counts(changes):
    data = payload(**changes)
    response = api_request("POST", "/api/v1/recommend", json=data)
    assert response.status_code == 422
    if set(changes).issubset(
        {
            "productos_esenciales_totales",
            "productos_esenciales_disponibles",
            "productos_disponibles",
        }
    ):
        assert validate_payload(data)


def test_streamlit_client_calls_fastapi_http_contract_without_network(monkeypatch):
    def fake_post(url, *, json, timeout, headers, allow_redirects):
        assert allow_redirects is False
        assert url == "http://testserver/api/v1/recommend"
        assert timeout > 0
        return api_request("POST", "/api/v1/recommend", json=json, headers=headers)

    monkeypatch.setattr("demo.streamlit_app.requests.post", fake_post)
    monkeypatch.setattr("demo.streamlit_app.api_auth_headers", lambda: {})
    zero_essentials = payload(
        productos_esenciales_totales=0,
        productos_esenciales_disponibles=0,
        productos_disponibles=9,
    )
    assert validate_payload(zero_essentials) == []

    recommendation = call_recommendation_api(
        zero_essentials, base_url="http://testserver"
    )
    assert recommendation["winning_rule"] == "R06"
    assert recommendation["hechos_derivados"]["porcentaje_esenciales_disponibles"] == 100


def test_streamlit_renders_scenario_selection_without_a_server():
    script_path = Path(__file__).resolve().parents[1] / "demo" / "streamlit_app.py"
    at = AppTest.from_file(str(script_path)).run(timeout=20)
    assert not at.exception
    assert at.selectbox
    assert "Compra ideal" in at.selectbox[0].options
