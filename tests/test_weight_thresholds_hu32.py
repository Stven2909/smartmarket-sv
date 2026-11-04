"""HU-32: rounded display cannot change strict weighted-rule thresholds.

A 0.01-point display rounding is not evidence that a 50/60/75 policy
threshold was reached. An ulp-sized binary error at the exact threshold
must not exclude an otherwise qualifying alternative.
"""

from math import nextafter

import pytest

from app.expert_system.classifiers import derive_facts
from app.expert_system.convenience_index import (
    calculate_convenience_index,
    meets_convenience_threshold,
)
from app.expert_system.inference_engine import run_inference
from app.schemas.recommendation import RecommendationRequest

BASE = {
    "request_id": "hu32-limites",
    "alternativa_id": "tienda-limite",
    "costo_total": 45.0,
    "presupuesto": 50.0,
    "ahorro": 14.499,
    "distancia_km": 6.0,
    "distancia_adicional_km": 6.0,
    "tiempo_estimado_min": 35.0,
    "productos_disponibles": 10,
    "productos_totales": 10,
    "productos_esenciales_disponibles": 5,
    "productos_esenciales_totales": 5,
    "numero_supermercados": 1,
    "promociones_aplicables": False,
}


def request(**changes):
    return RecommendationRequest.model_validate({**BASE, **changes})


@pytest.mark.parametrize(
    ("rule_id", "threshold", "fact", "changes", "low", "high"),
    [
        (
            "R14", 75.0, "conveniencia_alta",
            {}, 14.499, 14.5,
        ),
        (
            "R15", 50.0, "conveniencia_no_baja",
            {"distancia_km": 7.9, "distancia_adicional_km": 7.9,
             "tiempo_estimado_min": 44.9}, 2.006, 2.01,
        ),
        (
            "R16", 60.0, "conveniencia_solida",
            {"distancia_km": 5.0, "distancia_adicional_km": 5.0,
             "tiempo_estimado_min": 30.0, "productos_disponibles": 8,
             "productos_esenciales_disponibles": 3,
             "productos_esenciales_totales": 3}, 7.855, 7.86,
        ),
    ],
)
def test_weighted_rules_respect_raw_threshold_not_display(
    rule_id, threshold, fact, changes, low, high,
):
    below = request(**changes, ahorro=low)
    at_or_above = request(**changes, ahorro=high)
    score_below = calculate_convenience_index(below)
    score_after = calculate_convenience_index(at_or_above)
    assert score_below["indice_conveniencia"] == threshold
    assert score_after["indice_conveniencia"] >= threshold

    facts_below = derive_facts(below)
    facts_after = derive_facts(at_or_above)
    assert facts_below[fact] is False
    assert facts_after[fact] is True

    outcome_below = run_inference(below)
    outcome_after = run_inference(at_or_above)
    assert rule_id not in outcome_below["activated_rules"]
    assert outcome_below["level"] == "NO_RECOMENDABLE"
    assert outcome_below["winning_rule"] is None
    assert outcome_after["winning_rule"] == rule_id
    assert outcome_after["level"] == "BUENA"


@pytest.mark.parametrize("threshold", [50.0, 60.0, 75.0])
def test_only_binary_float_noise_gets_tolerance(threshold):
    assert meets_convenience_threshold(threshold, threshold)
    assert meets_convenience_threshold(nextafter(threshold, 0.0), threshold)
    assert not meets_convenience_threshold(threshold - 1e-8, threshold)
    assert not meets_convenience_threshold(threshold - 0.004, threshold)


def test_r14_exact_mathematical_boundary_survives_float_roundoff():
    # The normalized weighted sum for these 14 facts is mathematically 75,
    # but binary floating-point arithmetic may yield 74.99999999999999.
    item = request(ahorro=14.5)
    raw = 100 * sum(
        part * calculate_convenience_index(item)["pesos"][key]
        for key, part in calculate_convenience_index(item)[
            "componentes_conveniencia"
        ].items()
    )
    assert abs(raw - 75) < 1e-12
    assert derive_facts(item)["conveniencia_alta"] is True
    assert run_inference(item)["winning_rule"] == "R14"
