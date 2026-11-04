"""HU-30: weights affect qualifying rules while critical decisions dominate."""

import json
from pathlib import Path

import pytest

from app.expert_system.classifiers import derive_facts
from app.expert_system.convenience_config import DEFAULT_CONVENIENCE_CONFIG
from app.expert_system.convenience_index import (
    calculate_convenience_index,
    meets_convenience_threshold,
)
from app.schemas.recommendation import RecommendationRequest, RecommendationResponse
from app.services.recommendation_service import recommend
from scripts.check_inference_consistency import check_inference_consistency

ROOT = Path(__file__).resolve().parents[1]
BASE = {
    "request_id": "weighted-sample",
    "alternativa_id": "weighted-store",
    "costo_total": 45.0,
    "presupuesto": 50.0,
    "ahorro": 20.0,
    "distancia_km": 6.0,
    "distancia_adicional_km": 6.0,
    "tiempo_estimado_min": 35.0,
    "productos_disponibles": 10,
    "productos_totales": 10,
    "productos_esenciales_disponibles": 6,
    "productos_esenciales_totales": 6,
    "numero_supermercados": 1,
    "promociones_aplicables": False,
}


def scenario(**changes):
    return RecommendationRequest.model_validate({**BASE, **changes})


@pytest.mark.parametrize(
    ("changes", "winner", "expected_index"),
    [
        ({}, "R14", 84.62),
        ({"ahorro": 2.5, "distancia_km": 5, "distancia_adicional_km": 5,
          "tiempo_estimado_min": 30}, "R15", 55.62),
        ({"ahorro": 7, "productos_disponibles": 9, "distancia_km": 4,
          "distancia_adicional_km": 4, "tiempo_estimado_min": 30}, "R16", 62.0),
    ],
)
def test_weighted_rules_actually_win_the_right_scenarios(
    changes, winner, expected_index
):
    request = scenario(**changes)
    response = recommend(request)
    assert response.winning_rule == winner
    assert response.nivel_recomendacion == "BUENA"
    assert response.indice_conveniencia == pytest.approx(expected_index, abs=0.01)
    assert check_inference_consistency(request, response) == []


@pytest.mark.parametrize(
    ("winning_case", "lower_weighted", "specific_rule"),
    [
        (
            {},
            {"ahorro": 10.0},
            "R14",
        ),
        (
            {"ahorro": 2.5, "distancia_km": 5, "distancia_adicional_km": 5,
             "tiempo_estimado_min": 30},
            {"ahorro": 0, "distancia_km": 7.9, "distancia_adicional_km": 7.9,
             "tiempo_estimado_min": 44.9},
            "R15",
        ),
        (
            {"ahorro": 7, "productos_disponibles": 9, "distancia_km": 4,
             "distancia_adicional_km": 4, "tiempo_estimado_min": 30},
            {"ahorro": 3, "productos_disponibles": 8, "distancia_km": 5,
             "distancia_adicional_km": 5, "tiempo_estimado_min": 30},
            "R16",
        ),
    ],
)
def test_score_changes_decision_without_changing_every_boolean_condition(
    winning_case, lower_weighted, specific_rule
):
    favorable = scenario(**winning_case)
    unfavorable = scenario(**lower_weighted)
    a = recommend(favorable)
    b = recommend(unfavorable)
    assert a.winning_rule == specific_rule
    assert b.winning_rule is None
    assert b.nivel_recomendacion == "NO_RECOMENDABLE"
    assert a.indice_conveniencia > b.indice_conveniencia
    assert specific_rule not in b.reglas_activadas
    assert check_inference_consistency(unfavorable, b) == []


@pytest.mark.parametrize(
    ("change", "winner"),
    [
        ({"costo_total": 56}, "R01"),
        ({"productos_disponibles": 9, "productos_esenciales_disponibles": 5}, "R02"),
        ({"numero_supermercados": 3}, "R05"),
    ],
)
def test_weighted_good_score_never_overrides_critical_rules(change, winner):
    request = scenario(**change)
    result = recommend(request)
    assert result.winning_rule == winner
    assert result.nivel_recomendacion == "NO_RECOMENDABLE"
    assert check_inference_consistency(request, result) == []


def test_weights_are_normalized_and_boolean_facts_follow_same_index():
    weights = DEFAULT_CONVENIENCE_CONFIG.weights()
    assert weights == {
        "ahorro": 0.35,
        "disponibilidad": 0.25,
        "distancia": 0.20,
        "tiempo": 0.15,
        "promociones": 0.05,
    }
    assert sum(weights.values()) == pytest.approx(1.0)
    for request in [
        scenario(),
        scenario(ahorro=10),
        scenario(ahorro=0, distancia_adicional_km=7.9, tiempo_estimado_min=44.9),
    ]:
        facts = derive_facts(request)
        score = calculate_convenience_index(request)
        assert facts["conveniencia_alta"] is (
            score["clasificacion_conveniencia"] == "ALTA_CONVENIENCIA"
        )
        assert facts["conveniencia_no_baja"] is (
            score["clasificacion_conveniencia"] != "BAJA_CONVENIENCIA"
        )
        raw_score = 100 * sum(
            score["pesos"][factor] * component
            for factor, component in score["componentes_conveniencia"].items()
        )
        assert facts["conveniencia_solida"] is meets_convenience_threshold(
            raw_score, 60
        )


def test_all_new_rule_examples_are_reproducible_with_existing_contract():
    rows = json.loads((ROOT / "data" / "scenarios_hu30.json").read_text(encoding="utf-8"))
    assert len(rows) == 3
    assert len(RecommendationRequest.model_fields) == 14
    assert len(RecommendationResponse.model_fields) == 16
    actual = []
    for row in rows:
        request = RecommendationRequest.model_validate(row["facts"])
        result = recommend(request)
        actual.append(result.winning_rule)
        assert len(result.trace) == 16
        assert check_inference_consistency(request, result) == []
    assert actual == ["R14", "R15", "R16"]
