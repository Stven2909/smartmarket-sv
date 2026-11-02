"""Pruebas del caso provisional y del diagnóstico de cobertura de reglas."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

from app.schemas.comparison import ComparisonRequest
from app.schemas.recommendation import RecommendationRequest
from app.services.comparison_service import compare_alternatives
from app.services.recommendation_service import recommend
from demo.streamlit_app import build_coverage_report, load_scenarios


BASE = {
    "request_id": "diagnostico-001",
    "alternativa_id": "sucursal-a",
    "costo_total": 45.0,
    "presupuesto": 50.0,
    "ahorro": 5.0,
    "distancia_km": 5.0,
    "distancia_adicional_km": 4.0,
    "tiempo_estimado_min": 30,
    "productos_disponibles": 10,
    "productos_totales": 10,
    "productos_esenciales_disponibles": 6,
    "productos_esenciales_totales": 6,
    "numero_supermercados": 1,
    "promociones_aplicables": False,
}


def case(**changes):
    return RecommendationRequest.model_validate({**BASE, **changes})


def test_budget_slightly_exceeded_has_explicit_provisional_explanation():
    report = recommend(case(costo_total=53.0))
    assert report.nivel_recomendacion == "NO_RECOMENDABLE"
    assert report.winning_rule is None
    assert report.reglas_activadas == []
    assert report.prioridad_aplicada == "SIN_REGLA"
    assert "supera ligeramente" in report.explicacion
    assert "provisional" in report.explicacion
    assert "Ajustar" in report.accion_sugerida
    assert len(report.trace) == 8


def test_exact_budget_threshold_remains_provisional_and_above_is_critical():
    at_limit = recommend(case(costo_total=55.0))
    beyond = recommend(case(costo_total=55.01))
    assert at_limit.winning_rule is None
    assert "supera ligeramente" in at_limit.explicacion
    assert beyond.winning_rule == "R01"
    assert beyond.nivel_recomendacion == "NO_RECOMENDABLE"


def test_normal_unmatched_case_keeps_existing_generic_fallback():
    report = recommend(case())
    assert report.winning_rule is None
    assert report.accion_sugerida == "Comparar con otras alternativas antes de decidir."
    assert "Ninguna regla" in report.explicacion


def test_coverage_matrix_runs_all_example_cases_without_laravel():
    scenarios = load_scenarios()
    result = compare_alternatives(
        ComparisonRequest(
            alternativas=[
                RecommendationRequest.model_validate(item["facts"])
                for item in scenarios
            ]
        )
    )
    coverage = build_coverage_report(result.model_dump(mode="json"), scenarios)
    assert coverage["total"] == len(scenarios) == 9
    assert coverage["no_winner"] == 1
    assert coverage["conflicts"] >= 1
    assert {row["Regla"] for row in coverage["rules"]} == {
        f"R{index:02}" for index in range(1, 9)
    }
    assert all(row["Activaciones"] >= 1 for row in coverage["rules"])
    assert all(row["Victorias"] >= 1 for row in coverage["rules"])
    assert all(row["Ganadora"] for row in coverage["scenarios"])
    assert any(
        row["Ganadora"] == "Sin regla" for row in coverage["scenarios"]
    )


def test_streamlit_coverage_controls_load_without_network():
    script = Path(__file__).resolve().parents[1] / "demo" / "streamlit_app.py"
    at = AppTest.from_file(str(script)).run(timeout=20)
    assert not at.exception
    assert len(at.tabs) == 4
    assert any(button.label == "Evaluar cobertura" for button in at.button)
