import json

import pytest
from pydantic import ValidationError

from app.expert_system.classifiers import (
    THRESHOLDS,
    THRESHOLDS_VERSION,
    derive_facts,
)
from app.expert_system.inference_engine import InferenceError, run_inference
from app.expert_system.models import DERIVED_FACT_NAMES
from app.expert_system.rule_loader import load_rules
from app.schemas.levels import RECOMMENDATION_LEVELS
from app.schemas.recommendation import (
    RecommendationLevel as SchemaRecommendationLevel,
    RecommendationRequest,
    RecommendationResponse,
)
from app.expert_system.models import (
    RecommendationLevel as RuleRecommendationLevel,
)


VALID_REQUEST = {
    "request_id": "hardening-001",
    "alternativa_id": "supermercado-1",
    "costo_total": 42.50,
    "presupuesto": 50.00,
    "ahorro": 5.00,
    "distancia_km": 2.3,
    "distancia_adicional_km": 0.8,
    "tiempo_estimado_min": 12,
    "productos_disponibles": 10,
    "productos_totales": 10,
    "productos_esenciales_disponibles": 6,
    "productos_esenciales_totales": 6,
    "numero_supermercados": 1,
    "promociones_aplicables": False,
}


def make_request(**changes) -> RecommendationRequest:
    return RecommendationRequest.model_validate({**VALID_REQUEST, **changes})


def test_contract_rejects_null_budget_location_and_time():
    for field_name in (
        "presupuesto",
        "distancia_km",
        "distancia_adicional_km",
        "tiempo_estimado_min",
    ):
        with pytest.raises(ValidationError):
            RecommendationRequest.model_validate(
                {**VALID_REQUEST, field_name: None}
            )


def test_contract_accepts_zero_and_positive_savings_but_rejects_negative():
    assert make_request(ahorro=0).ahorro == 0
    assert make_request(ahorro=5).ahorro == 5

    with pytest.raises(ValidationError):
        make_request(ahorro=-0.01)


def test_response_accepts_numeric_facts_and_trace_fields():
    response = RecommendationResponse(
        request_id="hardening-002",
        nivel_recomendacion="BUENA",
        accion_sugerida="Comparar alternativas.",
        explicacion="La alternativa es válida.",
        reglas_activadas=["R07", "R08"],
        prioridad_aplicada="AHORRO_FRAGMENTACION",
        hechos_derivados={
            "dentro_presupuesto": True,
            "diferencia_presupuesto": 7.5,
            "porcentaje_exceso_presupuesto": 0.0,
        },
        version_reglas="1.0.0",
        winning_rule="R08",
        losing_rules=["R07"],
        trace=[
            {
                "rule_id": "R08",
                "evaluated": True,
                "activated": True,
                "conditions": {},
            }
        ],
    )

    assert response.winning_rule == "R08"
    assert response.losing_rules == ["R07"]
    assert response.trace[0]["activated"] is True


@pytest.mark.parametrize(
    ("ahorro", "expected"),
    [
        (2.99, "ahorro_bajo"),
        (3.00, "ahorro_medio"),
        (9.99, "ahorro_medio"),
        (10.00, "ahorro_alto"),
    ],
)
def test_savings_boundaries(ahorro, expected):
    facts = derive_facts(make_request(ahorro=ahorro))

    assert facts[expected] is True
    assert sum(
        facts[name] for name in ("ahorro_bajo", "ahorro_medio", "ahorro_alto")
    ) == 1


@pytest.mark.parametrize(
    ("distancia", "expected"),
    [
        (2.00, "distancia_cercana"),
        (2.01, "distancia_media"),
        (7.99, "distancia_media"),
        (8.00, "distancia_lejana"),
    ],
)
def test_distance_boundaries(distancia, expected):
    facts = derive_facts(make_request(distancia_adicional_km=distancia))

    assert facts[expected] is True
    assert sum(
        facts[name]
        for name in (
            "distancia_cercana",
            "distancia_media",
            "distancia_lejana",
        )
    ) == 1


@pytest.mark.parametrize(
    ("tiempo", "expected"),
    [
        (20.00, "tiempo_bajo"),
        (20.01, "tiempo_medio"),
        (44.99, "tiempo_medio"),
        (45.00, "tiempo_alto"),
    ],
)
def test_time_boundaries(tiempo, expected):
    facts = derive_facts(make_request(tiempo_estimado_min=tiempo))

    assert facts[expected] is True
    assert sum(
        facts[name] for name in ("tiempo_bajo", "tiempo_medio", "tiempo_alto")
    ) == 1


def test_budget_boundaries():
    slightly_exceeded = derive_facts(
        make_request(costo_total=110.00, presupuesto=100.00)
    )
    very_exceeded = derive_facts(
        make_request(costo_total=110.01, presupuesto=100.00)
    )

    assert slightly_exceeded["presupuesto_ligeramente_excedido"] is True
    assert slightly_exceeded["presupuesto_muy_excedido"] is False
    assert very_exceeded["presupuesto_ligeramente_excedido"] is False
    assert very_exceeded["presupuesto_muy_excedido"] is True


def test_fragmentation_boundary_is_three_supermarkets():
    two = derive_facts(make_request(numero_supermercados=2))
    three = derive_facts(make_request(numero_supermercados=3))

    assert two["compra_fragmentada"] is False
    assert three["compra_fragmentada"] is True


def test_derived_fact_names_have_one_checked_contract():
    facts = derive_facts(make_request())

    assert set(facts) == DERIVED_FACT_NAMES
    assert THRESHOLDS_VERSION == "1.0.0"
    assert THRESHOLDS["ahorro_bajo_max"] == 3.0


def test_recommendation_level_has_one_shared_definition():
    assert SchemaRecommendationLevel is RuleRecommendationLevel
    assert RECOMMENDATION_LEVELS == {
        "EXCELENTE",
        "BUENA",
        "NO_RECOMENDABLE",
    }


def test_r02_wins_over_r05_and_keeps_both_rules():
    result = run_inference(
        make_request(
            productos_esenciales_disponibles=5,
            numero_supermercados=3,
        )
    )

    assert result["activated_rules"] == ["R02", "R05"]
    assert result["winning_rule"] == "R02"
    assert result["losing_rules"] == ["R05"]
    assert result["level"] == "NO_RECOMENDABLE"


def test_r06_wins_over_r07_and_keeps_both_rules():
    result = run_inference(
        make_request(
            ahorro=11,
            promociones_aplicables=True,
        )
    )

    assert result["activated_rules"] == ["R06", "R07"]
    assert result["winning_rule"] == "R06"
    assert result["losing_rules"] == ["R07"]


def test_r08_wins_over_r07_when_two_stores_also_have_promotions():
    result = run_inference(
        make_request(
            ahorro=10,
            numero_supermercados=2,
            promociones_aplicables=True,
        )
    )

    assert result["activated_rules"] == ["R07", "R08"]
    assert result["winning_rule"] == "R08"
    assert result["losing_rules"] == ["R07"]


def test_default_conclusion_explains_that_no_specific_rule_was_triggered():
    result = run_inference(
        make_request(
            costo_total=45,
            ahorro=5,
            distancia_adicional_km=4,
            tiempo_estimado_min=30,
        )
    )

    assert result["level"] == "NO_RECOMENDABLE"
    assert result["winning_rule"] is None
    assert "Ninguna regla específica" in result["explanation"]
    assert "provisionalmente" in result["explanation"]


def test_trace_contains_full_evaluation_information_for_every_rule():
    result = run_inference(make_request())

    assert len(result["trace"]) == len(load_rules())
    for rule_trace in result["trace"]:
        assert {
            "rule_id",
            "evaluated",
            "activated",
            "conditions",
            "matched_conditions",
            "unmatched_conditions",
            "reason",
        }.issubset(rule_trace)
        for condition in rule_trace["conditions"].values():
            assert {"expected", "actual", "matched"}.issubset(condition)


def test_missing_fact_fails_before_returning_a_partial_decision():
    rules = load_rules()
    request = make_request()

    with pytest.raises(InferenceError, match="hechos inexistentes"):
        from app.expert_system.inference_engine import evaluate_rule

        evaluate_rule(rules[0], {"dentro_presupuesto": True})


def test_reversing_rules_file_does_not_change_result_or_trace_order(tmp_path):
    rules = [rule.model_dump() for rule in reversed(load_rules())]
    reversed_path = tmp_path / "rules-reversed.json"
    reversed_path.write_text(json.dumps(rules), encoding="utf-8")

    request = make_request(ahorro=11, promociones_aplicables=True)
    original = run_inference(request)
    reversed_result = run_inference(request, rules_path=reversed_path)

    assert reversed_result == original
