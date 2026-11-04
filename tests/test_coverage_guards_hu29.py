"""HU-29: avoid declaring a materially incomplete purchase EXCELENTE.

This suite uses only the existing 14 Laravel facts. No new API input fields.
"""

import json
from pathlib import Path

import pytest

from app.expert_system.classifiers import THRESHOLDS, derive_facts
from app.expert_system.convenience_index import CRITICAL_RULE_IDS
from app.schemas.recommendation import RecommendationRequest, RecommendationResponse
from app.services.recommendation_service import recommend
from scripts.check_inference_consistency import check_inference_consistency

ROOT = Path(__file__).resolve().parents[1]

BASE = {
    "request_id": "hu29-edge",
    "alternativa_id": "sucursal-hu29",
    "costo_total": 45.0,
    "presupuesto": 50.0,
    "ahorro": 5.0,
    "distancia_km": 2.0,
    "distancia_adicional_km": 1.0,
    "tiempo_estimado_min": 12.0,
    "productos_disponibles": 6,
    "productos_totales": 10,
    "productos_esenciales_disponibles": 0,
    "productos_esenciales_totales": 0,
    "numero_supermercados": 1,
    "promociones_aplicables": False,
}


def case(**changes):
    return RecommendationRequest.model_validate({**BASE, **changes})


def test_without_defined_essentials_low_coverage_is_critical_even_if_r06_matches():
    request = case()
    response = recommend(request)
    assert response.winning_rule == "R12"
    assert response.nivel_recomendacion == "NO_RECOMENDABLE"
    assert "R06" in response.reglas_activadas
    assert "R12" in CRITICAL_RULE_IDS
    assert response.prioridad_aplicada == "DISPONIBILIDAD"
    assert "80%" in response.explicacion
    assert check_inference_consistency(request, response) == []


@pytest.mark.parametrize(
    "available,active",
    [
        (0, False),   # R09 and R10 already protect empty inventories.
        (4, True),
        (5, True),
        (7, True),
        (8, False),  # 80 percent is the inclusive safe boundary.
        (10, False),
    ],
)
def test_coverage_threshold_is_explicit_and_strict(available, active):
    request = case(productos_disponibles=available)
    facts = derive_facts(request)
    assert facts["cobertura_parcial_relevante"] is (available < 8)
    assert ("R12" in recommend(request).reglas_activadas) is active


def test_defined_essentials_with_partial_coverage_is_good_not_excellent():
    request = case(
        productos_esenciales_totales=3,
        productos_esenciales_disponibles=3,
        distancia_adicional_km=1,
        tiempo_estimado_min=12,
    )
    response = recommend(request)
    assert response.nivel_recomendacion == "BUENA"
    assert response.winning_rule == "R13"
    assert "R06" in response.reglas_activadas
    assert "opcionales" in response.accion_sugerida
    assert check_inference_consistency(request, response) == []


def test_r13_does_not_recommend_a_shop_when_essentials_are_missing():
    request = case(
        productos_esenciales_totales=4,
        productos_esenciales_disponibles=3,
    )
    response = recommend(request)
    assert response.winning_rule == "R02"
    assert "R13" not in response.reglas_activadas
    assert response.nivel_recomendacion == "NO_RECOMENDABLE"


@pytest.mark.parametrize(
    "changes",
    [
        {"productos_disponibles": 8},
        {"distancia_adicional_km": 6.0},
        {"tiempo_estimado_min": 31.0},
        {"costo_total": 53.0},
        {"numero_supermercados": 2},
    ],
)
def test_r13_only_applies_when_stated_conditions_are_satisfied(changes):
    request = case(
        productos_esenciales_totales=3,
        productos_esenciales_disponibles=3,
        **changes,
    )
    response = recommend(request)
    assert "R13" not in response.reglas_activadas


def test_new_scenarios_winners_and_contract_stay_compatible():
    scenarios = json.loads(
        (ROOT / "data" / "scenarios_hu29.json").read_text(encoding="utf-8")
    )
    assert len(scenarios) == 2
    assert THRESHOLDS["cobertura_parcial_relevante_pct"] == 80.0
    assert len(RecommendationRequest.model_fields) == 14
    assert len(RecommendationResponse.model_fields) == 16
    assert len({item["facts"]["alternativa_id"] for item in scenarios}) == 2
    assert [recommend(RecommendationRequest.model_validate(x["facts"])).winning_rule
            for x in scenarios] == ["R12", "R13"]
    for scenario in scenarios:
        request = RecommendationRequest.model_validate(scenario["facts"])
        assert check_inference_consistency(request, recommend(request)) == []
