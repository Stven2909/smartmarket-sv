"""Pruebas de robustez semántica e hipótesis de sensibilidad independientes."""

import asyncio
from math import inf, nan
from pathlib import Path

import httpx
import pytest
from pydantic import ValidationError
from streamlit.testing.v1 import AppTest

from app.chatbot.chatbot_service import chat
from app.chatbot.intent_detector import detect_intent
from app.main import app
from app.schemas.chatbot import ChatRequest
from app.schemas.recommendation import RecommendationRequest
from app.schemas.sensitivity import SensitivityRequest, SensitivityResponse
from app.services.recommendation_service import recommend
from app.services.sensitivity_service import analyze_sensitivity

BASE = {
    "request_id": "auditoria-develop",
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


def option(**changes):
    return RecommendationRequest.model_validate({**BASE, **changes})


def api_request(method, path, **kwargs):
    async def send():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            return await client.request(method, path, **kwargs)

    return asyncio.run(send())


@pytest.mark.parametrize(
    "message,expected",
    [
        ("¿Qué tan lejos queda esta tienda?", "DISTANCIA"),
        ("¿Hay promociones aplicables?", "PROMOCIONES"),
        ("¿Existen descuentos?", "PROMOCIONES"),
        ("¿Hay ofertas disponibles?", "PROMOCIONES"),
        ("¿Cuánto me ahorro?", "AHORRO"),
        ("¿Me alcanza el presupuesto?", "PRESUPUESTO"),
    ],
)
def test_chat_recognizes_shopping_intents_used_by_frontend(message, expected):
    assert detect_intent(message) == expected


@pytest.mark.parametrize("available", [True, False])
def test_chat_promotions_uses_only_real_boolean_facts(available):
    request = option(promociones_aplicables=available)
    response = chat(
        ChatRequest(
            message="¿Hay descuentos en esta tienda?",
            facts=request.model_dump(),
            recommendation=recommend(request),
        )
    )
    assert response.intent == "PROMOCIONES"
    assert response.supported is True
    assert ("Sí, hay promociones" in response.response) == available
    if available:
        assert "importe" in response.response
    else:
        assert "No se identificaron" in response.response


def test_chat_promotions_does_not_invent_missing_data():
    original = option()
    response = chat(
        ChatRequest(
            message="¿Qué ofertas hay?",
            facts={},
            recommendation=recommend(original),
        )
    )
    assert "No tengo datos suficientes" in response.response


@pytest.mark.parametrize(
    "changes,winning_rule,required_reason",
    [
        ({"costo_total": 56.0}, "R01", "supera ampliamente"),
        (
            {"productos_disponibles": 9, "productos_esenciales_disponibles": 5},
            "R02",
            "faltan productos esenciales",
        ),
        ({"distancia_adicional_km": 8, "ahorro": 1}, "R03", "recorrido adicional"),
        ({"tiempo_estimado_min": 50, "ahorro": 1}, "R04", "tiempo de traslado"),
        ({"numero_supermercados": 3}, "R05", "varias tiendas"),
    ],
)
def test_negative_explanation_uses_actual_winning_reason(
    changes, winning_rule, required_reason
):
    request = option(**changes)
    expert = recommend(request)
    assert expert.winning_rule == winning_rule
    response = chat(
        ChatRequest(
            message="¿Por qué no recomiendas esta opción?",
            facts=request.model_dump(),
            recommendation=expert,
        )
    )
    assert required_reason in response.response
    assert "No te recomiendo" in response.response
    assert not response.response.startswith(
        "No te recomiendo esta opción porque la compra está dentro"
    )


@pytest.mark.parametrize(
    "field", [
        "costo_total", "presupuesto", "ahorro", "distancia_km",
        "distancia_adicional_km", "tiempo_estimado_min",
    ],
)
@pytest.mark.parametrize("value", [inf, nan, -inf])
def test_non_finite_inputs_are_rejected_before_inference(field, value):
    with pytest.raises(ValidationError):
        option(**{field: value})


def test_sensitivity_is_deterministic_and_preserves_source_request():
    original = option()
    first = analyze_sensitivity(SensitivityRequest(alternativa=original))
    second = analyze_sensitivity(SensitivityRequest(alternativa=original))
    assert first.model_dump() == second.model_dump()
    assert original.costo_total == 42.5
    assert original.productos_esenciales_disponibles == 6
    assert first.escenario_base.winning_rule == "R06"
    assert len(first.escenarios) >= 5
    assert first.cantidad_decisiones_distintas >= 1
    assert all(len(case.recomendacion.trace) == 8 for case in first.escenarios)


def test_essential_unavailability_changes_decision_to_r02():
    report = analyze_sensitivity(SensitivityRequest(alternativa=option()))
    essential = next(
        row for row in report.escenarios if row.escenario == "falta_un_esencial"
    )
    assert essential.recomendacion.winning_rule == "R02"
    assert essential.recomendacion.nivel_recomendacion == "NO_RECOMENDABLE"
    assert essential.cambia_decision is True
    assert essential.cambios["productos_esenciales_disponibles"] == 5
    assert essential.cambios["productos_disponibles"] == 9


def test_sensitivity_without_essentials_never_invents_missing_essentials():
    case = option(
        productos_esenciales_totales=0,
        productos_esenciales_disponibles=0,
    )
    report = analyze_sensitivity(SensitivityRequest(alternativa=case))
    assert not any(
        item.escenario == "falta_un_esencial" for item in report.escenarios
    )


def test_sensitivity_uses_valid_cost_savings_consistency():
    original = option(ahorro=0)
    report = analyze_sensitivity(SensitivityRequest(alternativa=original))
    for row in report.escenarios:
        if row.escenario.startswith("precio_mas_"):
            assert row.cambios["ahorro"] == 0
            assert row.cambios["costo_total"] > original.costo_total


def test_public_sensitivity_http_preserves_existing_recommendation_keys():
    request = option()
    before = api_request(
        "POST", "/api/v1/recommend", json=request.model_dump()
    )
    response = api_request(
        "POST", "/api/v1/sensitivity",
        json={"alternativa": request.model_dump()},
    )
    assert before.status_code == response.status_code == 200
    parsed = SensitivityResponse.model_validate(response.json())
    assert parsed.escenario_base.model_dump(mode="json") == before.json()
    assert parsed.alternativa_id == request.alternativa_id
    assert parsed.cantidad_decisiones_distintas >= 1


def test_sensitivity_rejects_invalid_json_and_uses_existing_key(monkeypatch):
    bad = api_request("POST", "/api/v1/sensitivity", json={"alternativa": {}})
    assert bad.status_code == 422
    monkeypatch.setenv("SMARTMARKET_API_KEY", "prueba-academica")
    payload = {"alternativa": option().model_dump()}
    assert api_request(
        "POST", "/api/v1/sensitivity", json=payload
    ).status_code == 401
    assert api_request(
        "POST", "/api/v1/sensitivity", json=payload,
        headers={"X-API-Key": "prueba-academica"},
    ).status_code == 200


def test_streamlit_shows_sensitivity_tab_without_server():
    path = Path(__file__).resolve().parents[1] / "demo" / "streamlit_app.py"
    at = AppTest.from_file(str(path)).run(timeout=20)
    assert not at.exception
    assert len(at.tabs) == 4
