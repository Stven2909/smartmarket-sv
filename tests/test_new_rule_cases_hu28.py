"""HU-28: coverage safeguards and balanced no-promotion purchases."""

import asyncio

import httpx
import pytest

from app.expert_system.classifiers import THRESHOLDS, derive_facts
from app.main import app
from app.schemas.recommendation import RecommendationRequest, RecommendationResponse
from app.services.recommendation_service import recommend
from scripts.check_inference_consistency import check_inference_consistency

BASE = {
    "request_id": "hu28-caso",
    "alternativa_id": "tienda-prueba",
    "costo_total": 45.0,
    "presupuesto": 50.0,
    "ahorro": 5.0,
    "distancia_km": 5.0,
    "distancia_adicional_km": 4.0,
    "tiempo_estimado_min": 30.0,
    "productos_disponibles": 10,
    "productos_totales": 10,
    "productos_esenciales_disponibles": 6,
    "productos_esenciales_totales": 6,
    "numero_supermercados": 1,
    "promociones_aplicables": False,
}


def example(**overrides) -> RecommendationRequest:
    return RecommendationRequest.model_validate({**BASE, **overrides})


def test_r09_rejects_empty_store_even_if_nothing_is_marked_essential():
    item = example(
        costo_total=0,
        ahorro=0,
        productos_disponibles=0,
        productos_esenciales_disponibles=0,
        productos_esenciales_totales=0,
        distancia_adicional_km=1,
        tiempo_estimado_min=10,
        promociones_aplicables=True,
    )
    result = recommend(item)
    assert result.winning_rule == "R09"
    assert result.nivel_recomendacion == "NO_RECOMENDABLE"
    assert "R09" in result.reglas_activadas
    assert "R06" in result.reglas_activadas
    assert result.hechos_derivados["ningun_producto_disponible"]
    assert check_inference_consistency(item, result) == []


def test_r10_rejects_less_than_half_of_products_even_if_essentials_are_unmarked():
    item = example(
        productos_disponibles=4,
        productos_esenciales_totales=0,
        productos_esenciales_disponibles=0,
        promociones_aplicables=False,
    )
    result = recommend(item)
    assert result.winning_rule == "R10"
    assert result.nivel_recomendacion == "NO_RECOMENDABLE"
    assert result.hechos_derivados["cobertura_muy_baja"] is True
    assert check_inference_consistency(item, result) == []


@pytest.mark.parametrize(
    "available,low",
    [(0, True), (4, True), (5, False), (6, False), (10, False)],
)
def test_low_coverage_boundary_is_strictly_below_fifty_percent(available, low):
    facts = derive_facts(
        example(
            productos_disponibles=available,
            productos_esenciales_disponibles=0,
            productos_esenciales_totales=0,
        )
    )
    assert facts["cobertura_muy_baja"] is low
    assert THRESHOLDS["cobertura_muy_baja_max_pct"] == 50.0


def test_r11_recommends_complete_moderate_trip_without_promotion():
    item = example()
    result = recommend(item)
    assert result.nivel_recomendacion == "BUENA"
    assert result.winning_rule == "R11"
    assert result.reglas_activadas == ["R11"]
    assert "sin promociones" in result.explicacion
    assert check_inference_consistency(item, result) == []


@pytest.mark.parametrize(
    "changes",
    [
        {"distancia_adicional_km": 5.01},
        {"tiempo_estimado_min": 30.01},
        {"ahorro": 2.99},
        {"productos_disponibles": 9},
        {"numero_supermercados": 2},
    ],
)
def test_r11_requires_every_balanced_purchase_condition(changes):
    result = recommend(example(**changes))
    assert "R11" not in result.reglas_activadas


def test_r11_is_not_required_when_a_promotion_exists():
    result = recommend(example(promociones_aplicables=True))
    assert result.winning_rule == "R07"
    assert "R11" not in result.reglas_activadas


def test_r08_no_longer_claims_to_be_favorable_when_essentials_are_missing():
    item = example(
        numero_supermercados=2,
        ahorro=12,
        productos_disponibles=9,
        productos_esenciales_disponibles=5,
    )
    result = recommend(item)
    assert result.winning_rule == "R02"
    assert result.nivel_recomendacion == "NO_RECOMENDABLE"
    assert "R08" not in result.reglas_activadas
    assert check_inference_consistency(item, result) == []


def test_original_14_input_and_16_output_fields_are_preserved():
    assert len(RecommendationRequest.model_fields) == 14
    assert len(RecommendationResponse.model_fields) == 16


def test_http_response_exposes_same_decision_and_new_rules_version():
    async def send():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            return await client.post(
                "/api/v1/recommend",
                json=example().model_dump(mode="json"),
            )
    result = asyncio.run(send())
    assert result.status_code == 200
    payload = result.json()
    assert payload["winning_rule"] == "R11"
    assert payload["version_reglas"] == "1.2.0"
    assert payload["version_contrato"] == "1.0.0"
    assert len(payload["trace"]) == 13
    assert len(payload) == 16
