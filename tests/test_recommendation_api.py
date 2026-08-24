import asyncio

import httpx

from app.main import app
from app.schemas.recommendation import RecommendationResponse


def request(method: str, url: str, **kwargs):
    async def send_request():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            return await client.request(method, url, **kwargs)

    return asyncio.run(send_request())


VALID_REQUEST = {
    "request_id": "demo-001",
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


def post_recommendation(**changes):
    return request(
        "POST",
        "/api/v1/recommend",
        json={**VALID_REQUEST, **changes},
    )


def test_health_endpoint_still_works():
    response = request("GET", "/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_ideal_scenario_returns_http_200_and_excellent():
    response = post_recommendation()

    assert response.status_code == 200
    assert response.json()["nivel_recomendacion"] == "EXCELENTE"


def test_very_exceeded_budget_returns_not_recommended():
    response = post_recommendation(costo_total=56)

    assert response.status_code == 200
    assert response.json()["nivel_recomendacion"] == "NO_RECOMENDABLE"


def test_missing_essential_products_returns_not_recommended():
    response = post_recommendation(productos_esenciales_disponibles=5)

    assert response.status_code == 200
    assert response.json()["nivel_recomendacion"] == "NO_RECOMENDABLE"


def test_activated_rules_are_in_response():
    response = post_recommendation()

    assert response.status_code == 200
    assert "R06" in response.json()["reglas_activadas"]


def test_derived_facts_are_in_response():
    response = post_recommendation()
    facts = response.json()["hechos_derivados"]

    assert response.status_code == 200
    assert facts["dentro_presupuesto"] is True
    assert facts["porcentaje_productos_disponibles"] == 100.0
    assert facts["diferencia_presupuesto"] == 7.5


def test_response_conforms_to_recommendation_response():
    response = post_recommendation()
    parsed = RecommendationResponse.model_validate(response.json())

    assert parsed.request_id == "demo-001"
    assert parsed.version_reglas == "1.0.0"


def test_missing_required_field_returns_422():
    payload = {**VALID_REQUEST}
    del payload["presupuesto"]

    response = request("POST", "/api/v1/recommend", json=payload)

    assert response.status_code == 422


def test_invalid_value_returns_422():
    response = post_recommendation(presupuesto=0)

    assert response.status_code == 422


def test_unknown_field_returns_422():
    response = post_recommendation(campo_no_permitido=True)

    assert response.status_code == 422


def test_response_preserves_request_id():
    response = post_recommendation(request_id="request-api-007")

    assert response.status_code == 200
    assert response.json()["request_id"] == "request-api-007"


def test_endpoint_runs_without_laravel():
    response = post_recommendation()

    assert response.status_code == 200
    assert response.json()["version_reglas"] == "1.0.0"


def test_api_rejects_missing_or_wrong_key_when_configured(monkeypatch):
    monkeypatch.setenv("SMARTMARKET_API_KEY", "test-key")

    without_header = request("POST", "/api/v1/recommend", json=VALID_REQUEST)
    wrong_key = request(
        "POST",
        "/api/v1/recommend",
        json=VALID_REQUEST,
        headers={"X-API-Key": "wrong"},
    )

    assert without_header.status_code == 401
    assert wrong_key.status_code == 401


def test_api_accepts_correct_key_and_keeps_health_open(monkeypatch):
    monkeypatch.setenv("SMARTMARKET_API_KEY", "test-key")

    authorized = request(
        "POST",
        "/api/v1/recommend",
        json=VALID_REQUEST,
        headers={"X-API-Key": "test-key"},
    )
    health = request("GET", "/health")

    assert authorized.status_code == 200
    assert health.status_code == 200


def test_chat_also_requires_key(monkeypatch):
    monkeypatch.setenv("SMARTMARKET_API_KEY", "test-key")

    response = request(
        "POST",
        "/api/v1/chat",
        json={
            "message": "¿Por qué esta recomendación?",
            "facts": VALID_REQUEST,
            "recommendation": {},
        },
    )

    assert response.status_code == 401
