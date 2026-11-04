"""Regresión del diagnóstico sin afectar el contrato principal de Laravel."""

import asyncio
import json
from pathlib import Path

import httpx
import pytest
from streamlit.testing.v1 import AppTest

from app.main import app
from app.schemas.diagnosis import DiagnosisRequest, DiagnosisResponse
from app.schemas.recommendation import RecommendationRequest, RecommendationResponse
from app.services.diagnosis_service import diagnose
from app.services.recommendation_service import recommend

BASE = {
    "request_id": "diagnostico-hu",
    "alternativa_id": "sucursal-1",
    "costo_total": 42.5,
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


def request_api(method, path, **kwargs):
    async def send():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://localhost",
        ) as client:
            return await client.request(method, path, **kwargs)

    return asyncio.run(send())


def test_ideal_diagnosis_identifies_active_rules_without_risks():
    item = option()
    baseline = item.model_dump()
    diagnosis = diagnose(DiagnosisRequest(alternativa=item))
    assert diagnosis.alternativa_id == "sucursal-1"
    assert diagnosis.nivel_actual == "EXCELENTE"
    assert diagnosis.regla_ganadora == "R06"
    assert diagnosis.riesgos_criticos == []
    assert {row.regla for row in diagnosis.oportunidades} == {"R06", "R07", "R08", "R11", "R13"}
    assert [row.regla for row in diagnosis.oportunidades[:2]] == ["R06", "R07"]
    assert all(not row.faltantes for row in diagnosis.oportunidades[:2])
    assert item.model_dump() == baseline


def test_critical_risks_are_explained_and_not_overridden():
    item = option(
        numero_supermercados=2,
        productos_disponibles=9,
        productos_esenciales_disponibles=5,
    )
    report = diagnose(DiagnosisRequest(alternativa=item))
    assert report.nivel_actual == "NO_RECOMENDABLE"
    assert report.regla_ganadora == "R02"
    assert [risk.regla for risk in report.riesgos_criticos] == ["R02"]
    assert "no garantiza" in report.resumen
    r08 = next(row for row in report.oportunidades if row.regla == "R08")
    assert r08.activa is False
    assert any(x.hecho == "todos_esenciales_disponibles" for x in r08.faltantes)


def test_diagnosis_observes_multiple_critical_rules_in_priority_order():
    item = option(
        costo_total=56.0,
        numero_supermercados=3,
        productos_disponibles=9,
        productos_esenciales_disponibles=5,
    )
    result = diagnose(DiagnosisRequest(alternativa=item))
    assert result.regla_ganadora == "R01"
    assert [risk.regla for risk in result.riesgos_criticos] == [
        "R01", "R02", "R05"
    ]


def test_missing_essential_guidance_is_mathematically_correct():
    item = option(
        productos_disponibles=8,
        productos_esenciales_disponibles=4,
        promociones_aplicables=False,
    )
    result = diagnose(DiagnosisRequest(alternativa=item))
    r06 = next(row for row in result.oportunidades if row.regla == "R06")
    gap = next(x for x in r06.faltantes if x.hecho == "todos_esenciales_disponibles")
    assert "2 producto(s) esencial(es)" in gap.orientacion
    assert gap.valor_actual is False
    assert gap.valor_esperado is True


def test_promotion_guidance_does_not_invent_an_offer():
    report = diagnose(DiagnosisRequest(alternativa=option(promociones_aplicables=False)))
    r07 = next(row for row in report.oportunidades if row.regla == "R07")
    promotions = next(x for x in r07.faltantes if x.hecho == "promociones_relevantes")
    assert "Solo indicar que existen si fueron comprobadas" in promotions.orientacion
    assert "Descuento de" not in promotions.orientacion


def test_no_rule_case_returns_pending_requirements_instead_of_hallucinating():
    item = option(
        costo_total=45.0,
        ahorro=5.0,
        distancia_adicional_km=4.0,
        tiempo_estimado_min=30,
        productos_disponibles=9,
        promociones_aplicables=False,
    )
    report = diagnose(DiagnosisRequest(alternativa=item))
    assert report.regla_ganadora is None
    assert "Ninguna regla ganó" in report.resumen
    assert report.riesgos_criticos == []
    assert any(row.faltantes for row in report.oportunidades)


def test_optional_http_endpoint_has_valid_contract_and_no_emoji():
    payload = {"alternativa": option().model_dump()}
    original = request_api("POST", "/api/v1/recommend", json=payload["alternativa"])
    response = request_api("POST", "/api/v1/diagnosis", json=payload)
    assert original.status_code == 200
    assert response.status_code == 200
    result = DiagnosisResponse.model_validate(response.json())
    RecommendationResponse.model_validate(original.json())
    assert result.regla_ganadora == original.json()["winning_rule"]
    assert "R06" in json.dumps(response.json())
    assert not any(ord(c) > 0x1F000 for c in response.text)


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"alternativa": {}},
        {"alternativa": {**BASE, "precio_inventado": 42}},
    ],
)
def test_bad_diagnosis_inputs_are_rejected(payload):
    response = request_api("POST", "/api/v1/diagnosis", json=payload)
    assert response.status_code == 422


def test_diagnosis_respects_existing_api_key(monkeypatch):
    monkeypatch.setenv("SMARTMARKET_API_KEY", "clave-ci")
    data = {"alternativa": option().model_dump()}
    assert request_api("POST", "/api/v1/diagnosis", json=data).status_code == 401
    response = request_api(
        "POST", "/api/v1/diagnosis",
        json=data, headers={"X-API-Key": "clave-ci"},
    )
    assert response.status_code == 200


def test_new_diagnosis_does_not_change_recommendation_response_schema():
    spec = request_api("GET", "/openapi.json").json()
    models = spec["components"]["schemas"]
    assert "/api/v1/diagnosis" in spec["paths"]
    assert len(models["RecommendationRequest"]["properties"]) == 14
    assert len(models["RecommendationResponse"]["properties"]) == 16
    assert set(models["DiagnosisRequest"]["properties"]) == {"alternativa"}


def test_streamlit_shows_diagnosis_control_with_a_previous_result():
    script = Path(__file__).resolve().parents[1] / "demo" / "streamlit_app.py"
    at = AppTest.from_file(str(script))
    at.session_state["latest_facts"] = BASE.copy()
    at.session_state["latest_recommendation"] = recommend(option()).model_dump(
        mode="json"
    )
    at.run(timeout=20)
    assert not at.exception
    assert len(at.tabs) == 4
    assert any(button.label == "Diagnosticar alternativa" for button in at.button)



def test_streamlit_diagnosis_uses_fastapi_without_external_network(monkeypatch):
    import requests

    def fake_post(url, *, json, timeout, headers, allow_redirects):
        assert allow_redirects is False
        assert url.endswith("/api/v1/diagnosis")
        assert timeout > 0
        return request_api("POST", "/api/v1/diagnosis", json=json, headers=headers)

    monkeypatch.setattr(requests, "post", fake_post)
    script = Path(__file__).resolve().parents[1] / "demo" / "streamlit_app.py"
    at = AppTest.from_file(str(script))
    at.session_state["latest_facts"] = BASE.copy()
    at.session_state["latest_recommendation"] = recommend(option()).model_dump(
        mode="json"
    )
    at.run(timeout=20)
    assert not at.exception
    button = next(
        item for item in at.button if item.label == "Diagnosticar alternativa"
    )
    button.click()
    at.run(timeout=20)
    assert not at.exception
    assert at.session_state["latest_diagnosis"]["regla_ganadora"] == "R06"
    assert len(at.session_state["latest_diagnosis"]["oportunidades"]) == 4
