"""Comparador de alternativas y nueva demostración educativa sin Laravel."""

import asyncio
from pathlib import Path

import httpx
import pytest
from pydantic import ValidationError
from streamlit.testing.v1 import AppTest

from app.main import app
from app.schemas.comparison import ComparisonRequest, ComparisonResponse
from app.schemas.recommendation import RecommendationRequest, RecommendationResponse
from app.services.comparison_service import compare_alternatives

BASE = {
    "request_id": "comparacion-academica",
    "alternativa_id": "base",
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


def option(alternative_id, **changes):
    return RecommendationRequest.model_validate(
        {**BASE, "alternativa_id": alternative_id, **changes}
    )


def api_request(method, path, **kwargs):
    async def send():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            return await client.request(method, path, **kwargs)

    return asyncio.run(send())


def test_comparison_prefers_good_rule_over_critical_high_index():
    excellent = option("buena", ahorro=1.0, promociones_aplicables=False)
    critical = option("critica", costo_total=56.0, ahorro=20.0)
    result = compare_alternatives(
        ComparisonRequest(alternativas=[critical, excellent])
    )

    assert result.mejor_alternativa_id == "buena"
    assert [row.alternativa_id for row in result.ranking] == ["buena", "critica"]
    assert result.ranking[0].recomendacion.nivel_recomendacion == "EXCELENTE"
    assert result.ranking[1].riesgo_critico is True
    assert result.ranking[1].recomendacion.winning_rule == "R01"


def test_ranking_prioritizes_rule_then_fallback_then_critical():
    critical = option(
        "critica",
        productos_disponibles=9,
        productos_esenciales_disponibles=5,
    )
    provisional = option(
        "provisional",
        ahorro=5,
        distancia_adicional_km=4,
        tiempo_estimado_min=30,
        productos_disponibles=9,
        promociones_aplicables=False,
    )
    good = option(
        "buena",
        ahorro=5,
        distancia_adicional_km=4,
        tiempo_estimado_min=30,
    )
    excellent = option("excelente", promociones_aplicables=False)
    comparison = compare_alternatives(
        ComparisonRequest(alternativas=[critical, provisional, good, excellent])
    )
    assert [item.alternativa_id for item in comparison.ranking] == [
        "excelente",
        "buena",
        "provisional",
        "critica",
    ]
    assert comparison.ranking[2].recomendacion.winning_rule is None
    assert comparison.ranking[3].riesgo_critico is True


def test_ranking_is_deterministic_and_stable_under_input_permutation():
    a = option("a")
    b = option("b")
    ordered = compare_alternatives(ComparisonRequest(alternativas=[a, b]))
    reversed_order = compare_alternatives(ComparisonRequest(alternativas=[b, a]))
    assert [item.alternativa_id for item in ordered.ranking] == ["a", "b"]
    assert ordered.model_dump() == reversed_order.model_dump()


@pytest.mark.parametrize(
    "options",
    [
        [option("a")],
        [option("a"), option("a")],
        [option("a"), option("b", presupuesto=60.0)],
        [option(str(number)) for number in range(11)],
    ],
)
def test_comparison_rejects_invalid_groups(options):
    with pytest.raises(ValidationError):
        ComparisonRequest(alternativas=options)


def test_comparison_http_uses_existing_recommendation_contract_unchanged():
    payload = {
        "alternativas": [
            option("ideal").model_dump(),
            option(
                "no-recomendada",
                productos_disponibles=9,
                productos_esenciales_disponibles=5,
            ).model_dump(),
        ]
    }
    response = api_request("POST", "/api/v1/compare", json=payload)
    assert response.status_code == 200
    body = ComparisonResponse.model_validate(response.json())
    assert body.mejor_alternativa_id == "ideal"
    assert [row.posicion for row in body.ranking] == [1, 2]
    assert body.ranking[1].riesgo_critico
    for row in body.ranking:
        assert isinstance(row.recomendacion, RecommendationResponse)
        assert len(row.recomendacion.trace) == 13


def test_comparison_http_rejects_duplicate_ids_and_different_budgets():
    repeated = option("duplicada").model_dump()
    bad_ids = api_request(
        "POST", "/api/v1/compare", json={"alternativas": [repeated, repeated]}
    )
    assert bad_ids.status_code == 422

    mismatched = option("otra", presupuesto=60.0).model_dump()
    bad_budget = api_request(
        "POST", "/api/v1/compare",
        json={"alternativas": [repeated, mismatched]},
    )
    assert bad_budget.status_code == 422


def test_comparison_http_api_key_is_enforced(monkeypatch):
    monkeypatch.setenv("SMARTMARKET_API_KEY", "solo-pruebas")
    payload = {"alternativas": [option("a").model_dump(), option("b").model_dump()]}

    unauthorized = api_request("POST", "/api/v1/compare", json=payload)
    assert unauthorized.status_code == 401
    authorized = api_request(
        "POST", "/api/v1/compare",
        json=payload, headers={"X-API-Key": "solo-pruebas"},
    )
    assert authorized.status_code == 200


def test_demo_has_four_views_and_comparison_selection():
    script = Path(__file__).resolve().parents[1] / "demo" / "streamlit_app.py"
    at = AppTest.from_file(str(script))
    at.session_state["active_tab"] = "Comparador"
    at.run(timeout=20)
    assert not at.exception
    assert len(at.tabs) == 4
    assert at.multiselect
    assert len(at.multiselect[0].value) >= 2



def test_knowledge_endpoint_exposes_current_rules_and_parameters():
    response = api_request("GET", "/api/v1/knowledge")
    assert response.status_code == 200
    body = response.json()
    assert len(body["rules"]) == 13
    assert {rule["id"] for rule in body["rules"]} == {
        "R01", "R02", "R03", "R04", "R05", "R06", "R07", "R08", "R09", "R10", "R11", "R12", "R13"
    }
    assert sum(body["weights"].values()) == pytest.approx(1.0)
    assert body["thresholds"]["presupuesto_exceso_max_pct"] == 10.0
    assert body["rules_version"]
    assert body["convenience_version"]


def test_knowledge_endpoint_honors_existing_api_key(monkeypatch):
    monkeypatch.setenv("SMARTMARKET_API_KEY", "solo-pruebas")
    assert api_request("GET", "/api/v1/knowledge").status_code == 401
    response = api_request(
        "GET", "/api/v1/knowledge",
        headers={"X-API-Key": "solo-pruebas"},
    )
    assert response.status_code == 200


def test_streamlit_comparison_with_same_request_id_does_not_duplicate_widgets():
    script = Path(__file__).resolve().parents[1] / "demo" / "streamlit_app.py"
    report = compare_alternatives(
        ComparisonRequest(alternativas=[option("primera"), option("segunda")])
    )
    at = AppTest.from_file(str(script))
    at.session_state["active_tab"] = "Comparador"
    at.session_state["latest_comparison"] = report.model_dump(mode="json")
    at.run(timeout=20)
    assert not at.exception
