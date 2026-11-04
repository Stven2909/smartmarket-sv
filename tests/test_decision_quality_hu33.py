"""HU-33: explain unusual favorable decisions without changing the verdict."""

import pytest

from app.expert_system.classifiers import THRESHOLDS_VERSION
from app.expert_system.convenience_index import CRITICAL_RULE_IDS
from app.expert_system.decision_quality import (
    INCOMPLETE_EXCELLENT,
    LOW_INDEX,
    TRAVEL_REVIEW,
    decision_quality_flags,
)
from app.schemas.comparison import ComparisonRequest
from app.schemas.diagnosis import DiagnosisRequest
from app.schemas.recommendation import RecommendationRequest, RecommendationResponse
from app.schemas.versions import CONTRACT_VERSION, RULES_VERSION
from app.services.comparison_service import compare_alternatives
from app.services.diagnosis_service import diagnose
from app.services.recommendation_service import recommend

BASE = {
    "request_id": "hu33-demo",
    "alternativa_id": "viaje-largo",
    "costo_total": 45.0,
    "presupuesto": 50.0,
    "ahorro": 11.0,
    "distancia_km": 101.0,
    "distancia_adicional_km": 100.0,
    "tiempo_estimado_min": 200.0,
    "productos_disponibles": 10,
    "productos_totales": 10,
    "productos_esenciales_disponibles": 5,
    "productos_esenciales_totales": 5,
    "numero_supermercados": 1,
    "promociones_aplicables": True,
}


def scenario(**changes):
    return RecommendationRequest.model_validate({**BASE, **changes})


def flags_for(response):
    return decision_quality_flags(
        level=response.nivel_recomendacion,
        facts=response.hechos_derivados,
        convenience_classification=response.clasificacion_conveniencia,
    )


@pytest.mark.parametrize(
    ("changes", "rule", "score"),
    [
        ({}, "R07", 49.25),
        ({"numero_supermercados": 2, "promociones_aplicables": False}, "R08", 44.25),
    ],
)
def test_r07_r08_extreme_trips_are_flagged_without_overriding_decision(
    changes, rule, score,
):
    original = scenario(**changes)
    response = recommend(original)
    assert response.nivel_recomendacion == "BUENA"
    assert response.winning_rule == rule
    assert response.indice_conveniencia == pytest.approx(score)
    assert flags_for(response) == (TRAVEL_REVIEW, LOW_INDEX)
    assert "Aviso comercial:" in response.explicacion
    assert "100.00 km adicionales" in response.explicacion
    assert "200.00 min" in response.explicacion
    assert "índice ponderado es bajo" in response.explicacion
    assert response.reglas_activadas == [rule]
    assert len(response.trace) == 16
    assert len(response.model_dump()) == 16


@pytest.mark.parametrize(
    ("distance", "minutes", "should_warn"),
    [
        (7.99, 44.99, False),
        (8.0, 44.99, True),
        (7.99, 45.0, True),
        (8.01, 45.01, True),
    ],
)
def test_travel_flags_match_existing_exact_rule_boundaries(
    distance, minutes, should_warn,
):
    response = recommend(
        scenario(distancia_adicional_km=distance, tiempo_estimado_min=minutes)
    )
    assert response.winning_rule == "R07"
    assert (TRAVEL_REVIEW in flags_for(response)) is should_warn
    assert ("el trayecto de" in response.explicacion) is should_warn


def test_excellent_with_incomplete_list_explains_limitations():
    response = recommend(
        scenario(
            ahorro=1,
            distancia_km=1,
            distancia_adicional_km=1,
            tiempo_estimado_min=10,
            productos_disponibles=8,
            productos_esenciales_disponibles=1,
            productos_esenciales_totales=1,
            promociones_aplicables=False,
        )
    )
    assert response.nivel_recomendacion == "EXCELENTE"
    assert response.winning_rule == "R06"
    assert flags_for(response) == (INCOMPLETE_EXCELLENT,)
    assert "solo 80.0% de los productos" in response.explicacion
    assert "no a la lista completa" in response.explicacion


def test_critical_note_names_actual_winning_rule_not_first_active_rule():
    # R03 is encountered before R10 by sorted ID; R10 wins by priority.
    response = recommend(
        scenario(
            ahorro=1,
            distancia_adicional_km=9,
            tiempo_estimado_min=30,
            productos_disponibles=3,
            productos_esenciales_disponibles=1,
            productos_esenciales_totales=1,
            promociones_aplicables=False,
        )
    )
    assert response.winning_rule == "R10"
    assert "R03" in response.reglas_activadas
    assert "R10" in response.reglas_activadas
    assert response.winning_rule in CRITICAL_RULE_IDS
    assert "determinada por la regla R10" in response.explicacion
    assert "determinada por la regla R03" not in response.explicacion
    assert flags_for(response) == ()


def test_normal_favorable_alternative_is_not_flagged():
    response = recommend(
        scenario(
            alternativa_id="equilibrada",
            ahorro=11,
            distancia_km=1,
            distancia_adicional_km=1,
            tiempo_estimado_min=10,
            promociones_aplicables=False,
        )
    )
    assert response.winning_rule == "R06"
    assert flags_for(response) == ()
    assert "Aviso comercial:" not in response.explicacion


def test_optional_diagnosis_and_comparison_surface_flags_without_reranking():
    risky = scenario()
    balanced = scenario(
        alternativa_id="equilibrada",
        distancia_km=1,
        distancia_adicional_km=1,
        tiempo_estimado_min=10,
        promociones_aplicables=False,
    )
    diagnostic = diagnose(DiagnosisRequest(alternativa=risky))
    assert diagnostic.regla_ganadora == "R07"
    assert diagnostic.nivel_actual == "BUENA"
    assert len([note for note in diagnostic.advertencias if "Aviso comercial:" in note]) == 2

    comparison = compare_alternatives(ComparisonRequest(alternativas=[risky, balanced]))
    assert comparison.mejor_alternativa_id == "equilibrada"
    assert [row.alternativa_id for row in comparison.ranking] == [
        "equilibrada", "viaje-largo",
    ]
    assert "advertencias comerciales" in comparison.ranking[1].motivo_posicion
    assert any("1 alternativa(s) favorables" in note for note in comparison.advertencias)


def test_original_contract_and_weight_vector_are_preserved():
    assert len(RecommendationRequest.model_fields) == 14
    assert len(RecommendationResponse.model_fields) == 16
    outcome = recommend(scenario())
    assert outcome.pesos_conveniencia == {
        "ahorro": 0.35,
        "disponibilidad": 0.25,
        "distancia": 0.2,
        "tiempo": 0.15,
        "promociones": 0.05,
    }
    assert outcome.version_contrato == CONTRACT_VERSION == "1.0.0"
    assert outcome.version_reglas == RULES_VERSION == "1.3.2"
    assert THRESHOLDS_VERSION == "1.3.2"
