import pytest

from app.expert_system.conflict_resolver import resolve_conflicts
from app.expert_system.classifiers import derive_facts
from app.expert_system.inference_engine import (
    InferenceError,
    evaluate_rule,
    get_activated_rules,
    run_inference,
)
from app.expert_system.models import ProductionRule
from app.expert_system.rule_loader import load_rules
from app.schemas.recommendation import RecommendationRequest


VALID_REQUEST = {
    "request_id": "demo-001",
    "alternativa_id": "supermercado-1",
    "costo_total": 42.50,
    "presupuesto": 50.00,
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


def make_request(**changes) -> RecommendationRequest:
    return RecommendationRequest.model_validate({**VALID_REQUEST, **changes})


def rule(rule_id: str) -> ProductionRule:
    return next(item for item in load_rules() if item.id == rule_id)


def test_ideal_scenario_activates_r06_and_returns_excellent():
    result = run_inference(make_request())

    assert "R06" in result["activated_rules"]
    assert result["level"] == "EXCELENTE"
    assert result["winning_rule"] == "R06"
    assert result["priority_category"] == "CONVENIENCIA"


def test_very_exceeded_budget_activates_r01():
    result = run_inference(make_request(costo_total=56))

    assert "R01" in result["activated_rules"]
    assert result["level"] == "NO_RECOMENDABLE"
    assert result["winning_rule"] == "R01"


def test_missing_essentials_activates_r02():
    result = run_inference(
        make_request(productos_esenciales_disponibles=5)
    )

    assert "R02" in result["activated_rules"]
    assert result["level"] == "NO_RECOMENDABLE"
    assert result["winning_rule"] == "R02"


def test_far_distance_and_low_savings_activates_r03():
    result = run_inference(
        make_request(distancia_adicional_km=8, ahorro=2.99)
    )

    assert "R03" in result["activated_rules"]
    assert result["level"] == "NO_RECOMENDABLE"


def test_high_time_and_low_savings_activates_r04():
    result = run_inference(
        make_request(tiempo_estimado_min=45, ahorro=2.99)
    )

    assert "R04" in result["activated_rules"]
    assert result["level"] == "NO_RECOMENDABLE"


def test_fragmented_purchase_activates_r05():
    result = run_inference(make_request(numero_supermercados=3))

    assert "R05" in result["activated_rules"]
    assert result["level"] == "NO_RECOMENDABLE"


def test_promotions_activate_r07_when_no_higher_rule_wins():
    result = run_inference(
        make_request(
            ahorro=5,
            distancia_adicional_km=4,
            tiempo_estimado_min=30,
            promociones_aplicables=True,
        )
    )

    assert "R07" in result["activated_rules"]
    assert result["level"] == "BUENA"
    assert result["winning_rule"] == "R07"


def test_two_stores_with_high_savings_activate_r08():
    result = run_inference(
        make_request(numero_supermercados=2, ahorro=10)
    )

    assert "R08" in result["activated_rules"]
    assert result["level"] == "BUENA"
    assert result["winning_rule"] == "R08"


def test_conflict_resolver_prefers_r01_over_r06():
    # R01 y R06 son incompatibles con derive_facts; aquí se prueba
    # directamente la resolución determinista con ambos candidatos activados.
    conflict = resolve_conflicts([rule("R06"), rule("R01")])

    assert conflict["winner"].id == "R01"
    assert [item.id for item in conflict["losers"]] == ["R06"]


def test_no_rule_activated_uses_controlled_default():
    result = run_inference(
        make_request(
            costo_total=45,
            presupuesto=50,
            ahorro=5,
            distancia_adicional_km=4,
            tiempo_estimado_min=30,
            numero_supermercados=1,
            promociones_aplicables=False,
        )
    )

    assert result["activated_rules"] == []
    assert result["winning_rule"] is None
    assert result["level"] == "NO_RECOMENDABLE"
    assert "Ninguna regla" in result["explanation"]


def test_missing_fact_raises_clear_error():
    facts = {"dentro_presupuesto": True}
    invalid_rule = ProductionRule(
        id="RX",
        name="Regla con hecho inexistente",
        priority=1,
        category="PRUEBA",
        conditions={"hecho_inexistente": True},
        result={
            "level": "BUENA",
            "action": "Probar",
            "explanation": "Probar",
        },
    )

    with pytest.raises(InferenceError, match="hechos inexistentes"):
        evaluate_rule(invalid_rule, facts)


def test_same_request_produces_identical_result():
    request = make_request(ahorro=5, promociones_aplicables=True)

    assert run_inference(request) == run_inference(request)


def test_all_conditions_are_required_with_and_logic():
    r06 = rule("R06")
    facts = {
        "dentro_presupuesto": True,
        "todos_esenciales_disponibles": True,
        "distancia_cercana": True,
        "tiempo_bajo": True,
        "una_parada": False,
    }

    assert evaluate_rule(r06, facts) is False


def test_get_activated_rules_returns_all_matching_rules():
    facts = derive_facts(make_request())
    activated = get_activated_rules(load_rules(), facts)

    assert [item.id for item in activated] == ["R06", "R07"]


def test_trace_contains_condition_comparisons():
    result = run_inference(make_request())
    r06_trace = next(item for item in result["trace"] if item["rule_id"] == "R06")

    assert r06_trace["evaluated"] is True
    assert r06_trace["activated"] is True
    assert r06_trace["conditions"]["dentro_presupuesto"] == {
        "expected": True,
        "actual": True,
        "matched": True,
    }
