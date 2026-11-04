"""HU-31: reproducible sensitivity report and safe weighted inference."""

import json
import math
from dataclasses import replace

import pytest

from app.expert_system.classifiers import derive_facts
from app.expert_system.convenience_config import DEFAULT_CONVENIENCE_CONFIG
from app.expert_system.convenience_index import calculate_convenience_index
from app.expert_system.inference_engine import run_inference, run_inference_with_rules
from app.expert_system.rule_loader import load_rules
from app.schemas.recommendation import RecommendationRequest, RecommendationResponse
from scripts.calibrate_convenience_weights import (
    PROFILES,
    calibrate,
    configurations,
    load_cases,
    main,
    markdown_summary,
)


def test_profile_weights_are_explicit_finite_and_normalized():
    configs = configurations()
    assert set(configs) == set(PROFILES)
    assert len(configs) == 5
    assert configs["actual"] == DEFAULT_CONVENIENCE_CONFIG
    for config in configs.values():
        assert sum(config.weights().values()) == pytest.approx(1.0)
        assert all(0 <= weight <= 1 for weight in config.weights().values())


@pytest.mark.parametrize(
    "value",
    [float("nan"), float("inf"), -float("inf")],
)
def test_nonfinite_weights_or_reference_limits_are_rejected(value):
    with pytest.raises(ValueError):
        replace(DEFAULT_CONVENIENCE_CONFIG, peso_ahorro=value)
    with pytest.raises(ValueError):
        replace(DEFAULT_CONVENIENCE_CONFIG, tiempo_maximo=value)
    with pytest.raises(ValueError):
        replace(DEFAULT_CONVENIENCE_CONFIG, distancia_maxima=value)
    with pytest.raises(ValueError):
        replace(DEFAULT_CONVENIENCE_CONFIG, ahorro_referencia=value)


def test_original_inference_remains_exactly_the_same_under_default_profile():
    rules = load_rules()
    requests = load_cases()
    assert len(requests) == 17
    for _, request in requests:
        live = run_inference(request)
        trial = run_inference_with_rules(
            request, rules, config=DEFAULT_CONVENIENCE_CONFIG
        )
        assert trial == live
        assert trial["facts"] == derive_facts(request)
        assert trial["pesos_conveniencia"] == DEFAULT_CONVENIENCE_CONFIG.weights()


def test_custom_profile_affects_both_fact_classification_and_reported_index():
    rules = load_rules()
    request = load_cases()[-3][1]  # First HU-30 weighted scenario (R14).
    baseline = run_inference(request)
    trial = run_inference_with_rules(
        request,
        rules,
        config=configurations()["priorizar_promociones"],
    )
    assert trial["pesos_conveniencia"] == configurations()["priorizar_promociones"].weights()
    assert trial["facts"]["conveniencia_alta"] is False
    assert trial["indice_conveniencia"] != baseline["indice_conveniencia"]
    assert baseline["winning_rule"] == "R14"
    assert trial["winning_rule"] != "R14"
    assert set(trial["facts"]) == set(baseline["facts"])


def test_just_below_60_never_activates_r16_even_when_display_rounds_to_60():
    request = RecommendationRequest.model_validate({
        "request_id": "hu31-rounding",
        "alternativa_id": "hu31-store",
        "costo_total": 45,
        "presupuesto": 50,
        "ahorro": 7.855,
        "distancia_km": 5,
        "distancia_adicional_km": 5,
        "tiempo_estimado_min": 30,
        "productos_disponibles": 8,
        "productos_totales": 10,
        "productos_esenciales_disponibles": 3,
        "productos_esenciales_totales": 3,
        "numero_supermercados": 1,
        "promociones_aplicables": False,
    })
    assert calculate_convenience_index(request)["indice_conveniencia"] == 60.0
    assert derive_facts(request)["conveniencia_solida"] is False
    response = run_inference(request)
    assert "R16" not in response["activated_rules"]
    assert response["level"] == "NO_RECOMENDABLE"


def test_synthetic_profiles_are_deterministic_and_report_all_changes():
    cases = load_cases()
    first = calibrate(cases)
    second = calibrate(cases)
    assert first == second
    assert first["total_escenarios"] == 17
    assert first["decision"] == "MANTENER_PESOS_PRODUCCION_HASTA_TENER_ETIQUETAS_REALES"
    rows = first["perfiles"]
    current = rows[0]
    assert current["perfil"] == "actual"
    assert current["cambios_nivel"] == 0
    assert current["cambios_regla_ganadora"] == 0
    assert current["cambios_categoria_indice"] == 0
    assert current["variacion_media_indice_puntos"] == 0.0
    assert all(row["total"] == 17 for row in rows)
    assert all(row["violaciones_criticas"] == 0 for row in rows)
    assert all(row["protecciones_criticas_perdidas"] == 0 for row in rows)
    assert any(row["cambios_nivel"] > 0 for row in rows[1:])
    assert "no es una estimación" in markdown_summary(first).lower()


def test_critical_rejections_never_turn_positive_under_any_profile():
    cases = load_cases()
    rules = load_rules()
    for _, request in cases:
        for profile in configurations().values():
            result = run_inference_with_rules(request, rules, config=profile)
            if any(rule in {
                "R01", "R02", "R03", "R04", "R05",
                "R09", "R10", "R12",
            } for rule in result["activated_rules"]):
                assert result["level"] == "NO_RECOMENDABLE"
                assert result["winning_rule"] in {
                    "R01", "R02", "R03", "R04", "R05",
                    "R09", "R10", "R12",
                }


def test_reports_reject_empty_inputs_and_bad_example_limits():
    with pytest.raises(ValueError):
        calibrate([])
    with pytest.raises(ValueError):
        calibrate(load_cases(), max_examples=-1)
    with pytest.raises(ValueError):
        calibrate(load_cases(), max_examples=101)


def test_cli_writes_a_parseable_report_without_mutating_rules(tmp_path):
    output = tmp_path / "weight-calibration.json"
    assert main(["--json-output", str(output)]) == 0
    result = json.loads(output.read_text(encoding="utf-8"))
    assert len(result["perfiles"]) == 5
    assert result["total_escenarios"] == 17
    assert set(result) == {
        "version_reglas", "total_escenarios", "perfiles",
        "decision", "limitaciones",
    }


def test_weight_sensitivity_preserves_14_16_http_contract():
    assert len(RecommendationRequest.model_fields) == 14
    assert len(RecommendationResponse.model_fields) == 16
    assert math.isclose(sum(DEFAULT_CONVENIENCE_CONFIG.weights().values()), 1)
