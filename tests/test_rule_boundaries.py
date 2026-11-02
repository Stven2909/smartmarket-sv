"""Ensayos reproducibles de umbrales y robustez del sistema experto."""

from random import Random

import pytest

from app.expert_system.classifiers import derive_facts
from app.schemas.recommendation import RecommendationRequest
from app.services.recommendation_service import recommend

BASE = {
    "request_id": "umbral-001",
    "alternativa_id": "sucursal-test",
    "costo_total": 42.5,
    "presupuesto": 50.0,
    "ahorro": 5.0,
    "distancia_km": 2.5,
    "distancia_adicional_km": 1.0,
    "tiempo_estimado_min": 15,
    "productos_disponibles": 10,
    "productos_totales": 10,
    "productos_esenciales_disponibles": 6,
    "productos_esenciales_totales": 6,
    "numero_supermercados": 1,
    "promociones_aplicables": False,
}


def case(**overrides):
    return RecommendationRequest.model_validate({**BASE, **overrides})


@pytest.mark.parametrize(
    "cost,slightly,critical",
    [
        (50.0, False, False),
        (50.01, True, False),
        (55.0, True, False),
        (55.01, False, True),
    ],
)
def test_budget_critical_boundary_is_strictly_over_ten_percent(
    cost, slightly, critical
):
    facts = derive_facts(case(costo_total=cost))
    assert facts["presupuesto_ligeramente_excedido"] is slightly
    assert facts["presupuesto_muy_excedido"] is critical


@pytest.mark.parametrize(
    "distance,close,medium,far",
    [
        (2.0, True, False, False),
        (2.01, False, True, False),
        (7.99, False, True, False),
        (8.0, False, False, True),
    ],
)
def test_distance_boundaries(distance, close, medium, far):
    facts = derive_facts(case(distancia_adicional_km=distance))
    assert facts["distancia_cercana"] is close
    assert facts["distancia_media"] is medium
    assert facts["distancia_lejana"] is far


@pytest.mark.parametrize(
    "minutes,low,medium,high",
    [
        (20.0, True, False, False),
        (20.01, False, True, False),
        (44.99, False, True, False),
        (45.0, False, False, True),
    ],
)
def test_time_boundaries(minutes, low, medium, high):
    facts = derive_facts(case(tiempo_estimado_min=minutes))
    assert facts["tiempo_bajo"] is low
    assert facts["tiempo_medio"] is medium
    assert facts["tiempo_alto"] is high


@pytest.mark.parametrize(
    "saving,low,medium,high",
    [
        (2.99, True, False, False),
        (3.0, False, True, False),
        (9.99, False, True, False),
        (10.0, False, False, True),
    ],
)
def test_savings_boundaries(saving, low, medium, high):
    facts = derive_facts(case(ahorro=saving))
    assert facts["ahorro_bajo"] is low
    assert facts["ahorro_medio"] is medium
    assert facts["ahorro_alto"] is high


def test_deterministic_sample_of_one_hundred_consistent_alternatives():
    rng = Random(2026)
    for index in range(100):
        essential_total = rng.randint(0, 8)
        optional_total = rng.randint(1, 6)
        essential_available = rng.randint(0, essential_total)
        optional_available = rng.randint(0, optional_total)
        request = case(
            request_id=f"seed-2026-{index}",
            presupuesto=round(rng.uniform(10, 150), 2),
            costo_total=round(rng.uniform(0, 165), 2),
            ahorro=round(rng.uniform(0, 30), 2),
            distancia_km=round(rng.uniform(0, 30), 2),
            distancia_adicional_km=round(rng.uniform(0, 20), 2),
            tiempo_estimado_min=round(rng.uniform(0, 130), 2),
            productos_totales=essential_total + optional_total,
            productos_disponibles=essential_available + optional_available,
            productos_esenciales_totales=essential_total,
            productos_esenciales_disponibles=essential_available,
            numero_supermercados=rng.randint(1, 4),
            promociones_aplicables=rng.choice((True, False)),
        )
        first = recommend(request)
        second = recommend(request)
        assert first.model_dump() == second.model_dump()
        assert 0 <= first.indice_conveniencia <= 100
        assert len(first.trace) == 8
        assert set(first.reglas_activadas) == {
            trace["rule_id"] for trace in first.trace if trace["activated"]
        }
        if first.winning_rule is not None:
            assert first.winning_rule in first.reglas_activadas
        assert sum(first.pesos_conveniencia.values()) == pytest.approx(1)
