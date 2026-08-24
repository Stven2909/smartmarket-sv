import asyncio
import json
from pathlib import Path

import httpx
import pytest

from app.main import app
from app.schemas.recommendation import RecommendationResponse
from app.schemas.versions import CONTRACT_VERSION, RULES_VERSION

VALID_REQUEST = {
    "request_id": "contract-001",
    "alternativa_id": "supermercado-1",
    "costo_total": 42.50,
    "presupuesto": 50.00,
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


def api_request(method: str, path: str, **kwargs):
    async def send_request():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            return await client.request(method, path, **kwargs)

    return asyncio.run(send_request())


def payload(**changes):
    return {**VALID_REQUEST, **changes}


CONTRACT_CASES = [
    pytest.param({}, "EXCELENTE", "R06", "ALTA_CONVENIENCIA", id="ideal"),
    pytest.param({"costo_total": 56}, "NO_RECOMENDABLE", "R01", None, id="budget"),
    pytest.param(
        {"productos_esenciales_disponibles": 5},
        "NO_RECOMENDABLE",
        "R02",
        None,
        id="essentials",
    ),
    pytest.param(
        {"distancia_adicional_km": 8, "ahorro": 2.99},
        "NO_RECOMENDABLE",
        "R03",
        None,
        id="distance",
    ),
    pytest.param(
        {"tiempo_estimado_min": 45, "ahorro": 2.99},
        "NO_RECOMENDABLE",
        "R04",
        None,
        id="time",
    ),
    pytest.param(
        {"numero_supermercados": 3},
        "NO_RECOMENDABLE",
        "R05",
        None,
        id="fragmentation",
    ),
    pytest.param(
        {
            "ahorro": 5,
            "distancia_adicional_km": 4,
            "tiempo_estimado_min": 30,
            "promociones_aplicables": True,
        },
        "BUENA",
        "R07",
        "CONVENIENCIA_MEDIA",
        id="promotions",
    ),
    pytest.param(
        {"numero_supermercados": 2, "ahorro": 10},
        "BUENA",
        "R08",
        "ALTA_CONVENIENCIA",
        id="two-supermarkets",
    ),
    pytest.param(
        {
            "costo_total": 45,
            "ahorro": 5,
            "distancia_adicional_km": 4,
            "tiempo_estimado_min": 30,
            "promociones_aplicables": False,
        },
        "NO_RECOMENDABLE",
        None,
        "CONVENIENCIA_MEDIA",
        id="no-critical-rule",
    ),
    pytest.param({}, "EXCELENTE", "R06", "ALTA_CONVENIENCIA", id="high-index"),
    pytest.param(
        {
            "ahorro": 10,
            "distancia_adicional_km": 8,
            "tiempo_estimado_min": 60,
            "productos_disponibles": 8,
            "promociones_aplicables": False,
        },
        "NO_RECOMENDABLE",
        None,
        "CONVENIENCIA_MEDIA",
        id="medium-index",
    ),
    pytest.param(
        {
            "ahorro": 0,
            "distancia_adicional_km": 7,
            "tiempo_estimado_min": 44,
            "productos_disponibles": 5,
            "promociones_aplicables": False,
        },
        "NO_RECOMENDABLE",
        None,
        "BAJA_CONVENIENCIA",
        id="low-index",
    ),
    pytest.param(
        {"costo_total": 56},
        "NO_RECOMENDABLE",
        "R01",
        "ALTA_CONVENIENCIA",
        id="critical-high-index",
    ),
    pytest.param(
        {
            "ahorro": 0,
            "distancia_adicional_km": 20,
            "promociones_aplicables": False,
        },
        "NO_RECOMENDABLE",
        "R03",
        "BAJA_CONVENIENCIA",
        id="critical-low-index",
    ),
]


@pytest.mark.parametrize(
    ("changes", "expected_level", "expected_winner", "expected_classification"),
    CONTRACT_CASES,
)
def test_public_recommendation_contract_cases(
    changes,
    expected_level,
    expected_winner,
    expected_classification,
):
    response = api_request("POST", "/api/v1/recommend", json=payload(**changes))

    assert response.status_code == 200
    parsed = RecommendationResponse.model_validate(response.json())
    assert parsed.nivel_recomendacion == expected_level
    assert parsed.winning_rule == expected_winner
    if expected_classification:
        assert parsed.clasificacion_conveniencia == expected_classification


def test_public_response_exposes_the_frozen_contract_fields():
    response = api_request("POST", "/api/v1/recommend", json=payload())
    body = response.json()

    assert set(body) == {
        "request_id",
        "nivel_recomendacion",
        "accion_sugerida",
        "explicacion",
        "reglas_activadas",
        "prioridad_aplicada",
        "hechos_derivados",
        "version_reglas",
        "winning_rule",
        "losing_rules",
        "trace",
        "version_contrato",
        "indice_conveniencia",
        "clasificacion_conveniencia",
        "componentes_conveniencia",
        "pesos_conveniencia",
    }
    assert body["version_contrato"] == CONTRACT_VERSION
    assert body["version_reglas"] == RULES_VERSION
    assert isinstance(body["hechos_derivados"]["dentro_presupuesto"], bool)
    assert isinstance(body["hechos_derivados"]["diferencia_presupuesto"], float)
    assert isinstance(body["reglas_activadas"], list)
    assert isinstance(body["trace"], list)
    assert isinstance(body["componentes_conveniencia"], dict)
    assert isinstance(body["pesos_conveniencia"], dict)


def test_index_does_not_change_critical_rule_decision_fields():
    response = api_request(
        "POST",
        "/api/v1/recommend",
        json=payload(costo_total=56),
    )
    body = response.json()

    assert body["nivel_recomendacion"] == "NO_RECOMENDABLE"
    assert body["accion_sugerida"] == ("Replantear la lista o buscar productos sustitutos.")
    assert body["winning_rule"] == "R01"
    assert body["losing_rules"] == []
    assert body["reglas_activadas"] == ["R01"]
    assert body["trace"][0]["rule_id"] == "R01"
    assert "información complementaria" in body["explicacion"]


def test_same_public_request_returns_identical_response():
    request_payload = payload(ahorro=5, promociones_aplicables=True)

    first = api_request("POST", "/api/v1/recommend", json=request_payload)
    second = api_request("POST", "/api/v1/recommend", json=request_payload)

    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()


@pytest.mark.parametrize(
    "changes",
    [
        {"presupuesto": None},
        {"distancia_km": None},
        {"distancia_adicional_km": None},
        {"tiempo_estimado_min": None},
        {"latitud": None, "longitud": None},
    ],
)
def test_incomplete_backend_data_is_rejected_by_python_contract(changes):
    response = api_request("POST", "/api/v1/recommend", json=payload(**changes))

    assert response.status_code == 422


def test_openapi_contains_public_paths_models_versions_and_examples():
    schema = app.openapi()

    assert schema["info"]["version"] == CONTRACT_VERSION
    assert set(schema["paths"]) == {
        "/health",
        "/api/v1/recommend",
        "/api/v1/chat",
    }
    recommendation_post = schema["paths"]["/api/v1/recommend"]["post"]
    assert "422" in recommendation_post["responses"]
    assert "200" in recommendation_post["responses"]
    assert "examples" in recommendation_post["responses"]["200"]["content"]["application/json"]
    examples = recommendation_post["responses"]["200"]["content"]["application/json"]["examples"]
    assert {"alternativa_ideal", "regla_critica"} <= set(examples)

    request_schema = schema["components"]["schemas"]["RecommendationRequest"]
    response_schema = schema["components"]["schemas"]["RecommendationResponse"]
    assert request_schema["examples"]
    assert response_schema["examples"]
    assert "version_contrato" in response_schema["properties"]
    assert "indice_conveniencia" in response_schema["properties"]


def test_exported_openapi_and_integration_payload_files_are_valid():
    project_root = Path(__file__).resolve().parents[1]
    openapi = json.loads((project_root / "docs" / "openapi.json").read_text())
    payloads = json.loads((project_root / "docs" / "integration-payloads.json").read_text())

    assert openapi["info"]["version"] == CONTRACT_VERSION
    assert "/api/v1/recommend" in openapi["paths"]
    assert "requests" in payloads
    assert "responses" in payloads
