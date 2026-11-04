"""HU-34: evidence for how all 14 Laravel fields affect expert decisions.

Only synthetic, valid inputs. No changes to commercial rule priorities.
"""

import pytest

from app.expert_system.decision_quality import NO_ESSENTIALS_DEFINED, decision_quality_flags
from app.schemas.recommendation import RecommendationRequest, RecommendationResponse
from app.services.recommendation_service import recommend

BASE = {
    "request_id": "hu34-001",
    "alternativa_id": "local-1",
    "costo_total": 45.0,
    "presupuesto": 50.0,
    "ahorro": 11.0,
    "distancia_km": 2.0,
    "distancia_adicional_km": 1.0,
    "tiempo_estimado_min": 12.0,
    "productos_disponibles": 10,
    "productos_totales": 10,
    "productos_esenciales_disponibles": 5,
    "productos_esenciales_totales": 5,
    "numero_supermercados": 1,
    "promociones_aplicables": True,
}

IDENTITY_FIELDS = frozenset({"request_id", "alternativa_id"})
CONTEXT_FIELDS = frozenset({"distancia_km"})
EVALUATED_FIELDS = frozenset({
    "costo_total", "presupuesto", "ahorro", "distancia_adicional_km",
    "tiempo_estimado_min", "productos_disponibles", "productos_totales",
    "productos_esenciales_disponibles", "productos_esenciales_totales",
    "numero_supermercados", "promociones_aplicables",
})
WEIGHTED_FACTORS = {
    "ahorro": "ahorro",
    "productos_disponibles": "disponibilidad",
    "productos_totales": "disponibilidad",
    "distancia_adicional_km": "distancia",
    "tiempo_estimado_min": "tiempo",
    "promociones_aplicables": "promociones",
}


def case(**changes):
    return RecommendationRequest.model_validate({**BASE, **changes})


def flags_for(answer):
    return decision_quality_flags(
        level=answer.nivel_recomendacion,
        facts=answer.hechos_derivados,
        convenience_classification=answer.clasificacion_conveniencia,
    )


def test_all_fourteen_input_fields_are_classified_exclusively():
    public = set(RecommendationRequest.model_fields)
    assert len(public) == 14
    assert IDENTITY_FIELDS.isdisjoint(CONTEXT_FIELDS)
    assert IDENTITY_FIELDS.isdisjoint(EVALUATED_FIELDS)
    assert CONTEXT_FIELDS.isdisjoint(EVALUATED_FIELDS)
    assert public == IDENTITY_FIELDS | CONTEXT_FIELDS | EVALUATED_FIELDS
    assert set(WEIGHTED_FACTORS).issubset(EVALUATED_FIELDS)
    assert len(RecommendationResponse.model_fields) == 16


def test_identifiers_are_not_commercial_features():
    a = recommend(case())
    b = recommend(case(request_id="hu34-other", alternativa_id="other-store"))
    assert (a.winning_rule, a.nivel_recomendacion) == (
        b.winning_rule, b.nivel_recomendacion
    )
    assert a.indice_conveniencia == b.indice_conveniencia
    assert a.hechos_derivados == b.hechos_derivados
    assert a.reglas_activadas == b.reglas_activadas
    assert a.trace == b.trace
    assert a.explicacion == b.explicacion
    assert a.request_id != b.request_id


def test_absolute_distance_is_context_only_under_current_rules():
    original = recommend(case(distancia_km=1.0))
    altered = recommend(case(distancia_km=9999.0))
    assert altered.model_dump(mode="json") == original.model_dump(mode="json")


@pytest.mark.parametrize(
    ("changes", "expected_winner"),
    [
        ({"costo_total": 56.0}, "R01"),
        ({"presupuesto": 40.0}, "R01"),
        ({"productos_esenciales_disponibles": 4,
          "productos_disponibles": 9}, "R02"),
        ({"numero_supermercados": 3}, "R05"),
        ({"distancia_adicional_km": 8.0}, "R07"),
        ({"tiempo_estimado_min": 45.0}, "R07"),
    ],
)
def test_material_fields_can_change_winning_rule(changes, expected_winner):
    baseline = recommend(case())
    changed = recommend(case(**changes))
    assert baseline.winning_rule == "R06"
    assert changed.winning_rule == expected_winner
    assert changed.hechos_derivados != baseline.hechos_derivados


@pytest.mark.parametrize(
    "changes",
    [
        {"ahorro": 3},
        {"productos_disponibles": 9},
        {"productos_totales": 11},
        {"promociones_aplicables": False},
    ],
)
def test_weighted_components_reflect_changed_laravel_fields(changes):
    before = recommend(case())
    after = recommend(case(**changes))
    assert after.indice_conveniencia != before.indice_conveniencia
    assert after.componentes_conveniencia != before.componentes_conveniencia


@pytest.mark.parametrize(
    ("changes", "winner", "level"),
    [
        ({}, "R06", "EXCELENTE"),
        ({"distancia_adicional_km": 4.0,
          "tiempo_estimado_min": 30.0}, "R07", "BUENA"),
        ({"numero_supermercados": 2}, "R08", "BUENA"),
        ({"productos_disponibles": 7}, "R12", "NO_RECOMENDABLE"),
        ({"productos_disponibles": 8}, "R06", "EXCELENTE"),
    ],
)
def test_zero_essentials_semantics_are_explicit_and_critical_rules_still_win(
    changes, winner, level,
):
    sample = case(
        productos_esenciales_disponibles=0,
        productos_esenciales_totales=0,
        **changes,
    )
    result = recommend(sample)
    assert result.hechos_derivados["sin_esenciales_definidos"] is True
    assert result.hechos_derivados["todos_esenciales_disponibles"] is True
    assert result.winning_rule == winner
    assert result.nivel_recomendacion == level
    assert ("Aviso comercial: no se identificaron productos esenciales"
            in result.explicacion) is (level != "NO_RECOMENDABLE")
    assert (NO_ESSENTIALS_DEFINED in flags_for(result)) is (
        level != "NO_RECOMENDABLE"
    )
    assert len(result.trace) == 16


def test_explicit_essentials_do_not_trigger_undefined_essentials_warning():
    answer = recommend(case())
    assert NO_ESSENTIALS_DEFINED not in flags_for(answer)
    assert "no se identificaron productos esenciales" not in answer.explicacion
