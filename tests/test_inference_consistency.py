"""HU-25: R01-R08 decisions, traces and narratives cannot silently disagree."""

import json
from pathlib import Path

import pytest

from app.expert_system.rule_auditor import _representative_requests
from app.schemas.recommendation import RecommendationRequest, RecommendationResponse
from app.services.recommendation_service import recommend
from scripts.check_inference_consistency import check_inference_consistency

ROOT = Path(__file__).resolve().parents[1]
BASE = {
    "request_id": "hu25-001",
    "alternativa_id": "tienda-a",
    "costo_total": 42.5,
    "presupuesto": 50.0,
    "ahorro": 11.25,
    "distancia_km": 2.3,
    "distancia_adicional_km": 0.8,
    "tiempo_estimado_min": 12.0,
    "productos_disponibles": 10,
    "productos_totales": 10,
    "productos_esenciales_disponibles": 6,
    "productos_esenciales_totales": 6,
    "numero_supermercados": 1,
    "promociones_aplicables": True,
}


def scenario(**changes) -> RecommendationRequest:
    return RecommendationRequest.model_validate({**BASE, **changes})


def test_all_documented_scenarios_are_fully_consistent():
    cases = json.loads((ROOT / "data" / "scenarios.json").read_text(encoding="utf-8"))
    assert len(cases) >= 8
    for case in cases:
        request = RecommendationRequest.model_validate(case["facts"])
        result = recommend(request)
        assert not check_inference_consistency(request, result), case["id"]


def test_two_hundred_representative_combinations_have_coherent_explanations():
    scenarios = list(_representative_requests())
    assert len(scenarios) >= 200
    # The full grid has thousands of cases. Review deterministic coverage
    # across beginning, middle and end while keeping CI lightweight.
    indices = {i * (len(scenarios) - 1) // 199 for i in range(200)}
    for index in sorted(indices):
        request = scenarios[index]
        result = recommend(request)
        errors = check_inference_consistency(request, result)
        assert errors == [], (index, errors)


@pytest.mark.parametrize(
    "changes,winning",
    [
        ({}, "R06"),
        ({"costo_total": 56}, "R01"),
        (
            {"productos_disponibles": 9, "productos_esenciales_disponibles": 5},
            "R02",
        ),
        ({"ahorro": 2.99, "distancia_adicional_km": 8.0}, "R03"),
        ({"ahorro": 2.99, "tiempo_estimado_min": 45.0}, "R04"),
        ({"numero_supermercados": 3}, "R05"),
        (
            {"distancia_adicional_km": 4.0, "tiempo_estimado_min": 30.0},
            "R07",
        ),
        ({"numero_supermercados": 2}, "R08"),
        (
            {"distancia_adicional_km": 4.0, "tiempo_estimado_min": 30.0,
             "promociones_aplicables": False},
            None,
        ),
    ],
)
def test_every_rule_and_no_rule_case_is_consistent(changes, winning):
    request = scenario(**changes)
    result = recommend(request)
    assert result.winning_rule == winning
    assert check_inference_consistency(request, result) == []


@pytest.mark.parametrize(
    "field,corruption,violation",
    [
        ("request_id", "wrong-request", "request_id"),
        ("nivel_recomendacion", "BUENA", "nivel_recomendacion"),
        ("accion_sugerida", "Inventada", "accion_sugerida"),
        ("explicacion", "Cualquier recomendación", "explicacion"),
        ("winning_rule", "R03", "winning_rule"),
        ("losing_rules", ["R01"], "losing_rules"),
        ("reglas_activadas", [], "reglas_activadas"),
        ("prioridad_aplicada", "RANDOM", "prioridad_aplicada"),
        ("indice_conveniencia", 2.0, "indice_conveniencia"),
        ("clasificacion_conveniencia", "BAJA_CONVENIENCIA", "clasificacion"),
        ("componentes_conveniencia", {}, "componentes"),
        ("pesos_conveniencia", {}, "pesos"),
        ("hechos_derivados", {}, "hechos_derivados"),
    ],
)
def test_independent_audit_detects_tampered_response(field, corruption, violation):
    request = scenario()
    expected = recommend(request)
    tampered = expected.model_copy(update={field: corruption})
    findings = check_inference_consistency(request, tampered)
    assert any(violation in item for item in findings), findings


def test_independent_audit_detects_tampered_condition_trace():
    request = scenario()
    expected = recommend(request)
    traces = [dict(row) for row in expected.trace]
    trace = next(row for row in traces if row["rule_id"] == "R06")
    trace["conditions"] = {
        **trace["conditions"],
        "distancia_cercana": {
            "expected": True,
            "actual": False,
            "matched": False,
        },
    }
    tampered = expected.model_copy(update={"trace": traces})
    errors = check_inference_consistency(request, tampered)
    assert any("R06: evidencia incorrecta" in issue for issue in errors)


def test_public_request_response_shapes_stay_frozen():
    assert len(RecommendationRequest.model_fields) == 14
    assert len(RecommendationResponse.model_fields) == 16
    assert not check_inference_consistency(scenario(), recommend(scenario()))
