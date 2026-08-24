import pytest

from app.expert_system.convenience_config import (
    DEFAULT_CONVENIENCE_CONFIG,
    ConvenienceConfig,
)
from app.expert_system.convenience_index import (
    CONVENIENCE_CLASSIFICATIONS,
    calculate_convenience_index,
    normalize_availability,
    normalize_distance,
    normalize_promotions,
    normalize_savings,
    normalize_time,
)
from app.expert_system.inference_engine import run_inference
from app.schemas.recommendation import RecommendationRequest

VALID_REQUEST = {
    "request_id": "convenience-001",
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


def test_default_configuration_has_valid_weights_and_limits():
    config = DEFAULT_CONVENIENCE_CONFIG

    assert sum(config.weights().values()) == pytest.approx(1.0)
    assert config.ahorro_referencia > 0
    assert config.distancia_maxima > 0
    assert config.tiempo_maximo > 0


@pytest.mark.parametrize(
    "changes",
    [
        {"peso_ahorro": -0.1},
        {"peso_ahorro": 0.4},
        {"ahorro_referencia": 0},
        {"distancia_maxima": 0},
        {"tiempo_maximo": 0},
    ],
)
def test_invalid_configuration_is_rejected(changes):
    with pytest.raises(ValueError):
        ConvenienceConfig(**changes)


def test_savings_index_is_clamped_between_zero_and_one():
    assert normalize_savings(0) == 0
    assert normalize_savings(20) == pytest.approx(1)
    assert normalize_savings(25) == pytest.approx(1)


def test_availability_supports_complete_and_partial_values():
    assert normalize_availability(10, 10) == pytest.approx(1)
    assert normalize_availability(5, 10) == pytest.approx(0.5)


def test_distance_is_one_at_zero_and_zero_after_maximum():
    assert normalize_distance(0) == pytest.approx(1)
    assert normalize_distance(25) == pytest.approx(0)


def test_time_is_one_at_zero_and_zero_after_maximum():
    assert normalize_time(0) == pytest.approx(1)
    assert normalize_time(121) == pytest.approx(0)


def test_promotions_are_binary():
    assert normalize_promotions(True) == 1
    assert normalize_promotions(False) == 0


def test_ideal_case_returns_high_convenience_and_all_components_in_range():
    result = calculate_convenience_index(make_request())

    assert 0 <= result["indice_conveniencia"] <= 100
    assert result["clasificacion_conveniencia"] in CONVENIENCE_CLASSIFICATIONS
    assert set(result["componentes_conveniencia"]) == {
        "ahorro",
        "disponibilidad",
        "distancia",
        "tiempo",
        "promociones",
    }
    assert all(0 <= value <= 1 for value in result["componentes_conveniencia"].values())
    assert result["componentes_conveniencia"]["promociones"] == 1
    assert result["pesos"] == DEFAULT_CONVENIENCE_CONFIG.weights()


def test_unfavorable_case_returns_zero_or_low_convenience():
    result = calculate_convenience_index(
        make_request(
            ahorro=0,
            distancia_adicional_km=20,
            tiempo_estimado_min=120,
            productos_disponibles=0,
            promociones_aplicables=False,
        )
    )

    assert result["indice_conveniencia"] == 0
    assert result["clasificacion_conveniencia"] == "BAJA_CONVENIENCIA"
    assert all(value == 0 for value in result["componentes_conveniencia"].values())


@pytest.mark.parametrize(
    ("changes", "expected_rule"),
    [
        ({"costo_total": 56}, "R01"),
        ({"productos_esenciales_disponibles": 5}, "R02"),
        ({"distancia_adicional_km": 8, "ahorro": 2.99}, "R03"),
        ({"tiempo_estimado_min": 45, "ahorro": 2.99}, "R04"),
        ({"numero_supermercados": 3}, "R05"),
    ],
)
def test_critical_rule_keeps_original_conclusion_and_adds_context(
    changes,
    expected_rule,
):
    result = run_inference(make_request(**changes))

    assert result["winning_rule"] == expected_rule
    assert result["level"] == "NO_RECOMENDABLE"
    assert 0 <= result["indice_conveniencia"] <= 100
    assert f"regla {expected_rule}" in result["explanation"]
    assert "información complementaria" in result["explanation"]


def test_critical_index_does_not_change_r01():
    result = run_inference(make_request(costo_total=56))

    assert result["level"] == "NO_RECOMENDABLE"
    assert result["action"] == "Replantear la lista o buscar productos sustitutos."


def test_critical_index_does_not_change_r02():
    result = run_inference(make_request(productos_esenciales_disponibles=5))

    assert result["level"] == "NO_RECOMENDABLE"
    assert result["action"] == ("Buscar una alternativa con todos los productos esenciales.")


def test_critical_index_does_not_change_r03():
    result = run_inference(make_request(distancia_adicional_km=8, ahorro=2.99))

    assert result["level"] == "NO_RECOMENDABLE"
    assert result["winning_rule"] == "R03"


def test_critical_index_does_not_change_r04():
    result = run_inference(make_request(tiempo_estimado_min=45, ahorro=2.99))

    assert result["level"] == "NO_RECOMENDABLE"
    assert result["winning_rule"] == "R04"


def test_critical_index_does_not_change_r05():
    result = run_inference(make_request(numero_supermercados=3))

    assert result["level"] == "NO_RECOMENDABLE"
    assert result["winning_rule"] == "R05"


def test_non_critical_recommendation_is_only_enriched_by_index():
    result = run_inference(make_request())

    assert result["winning_rule"] == "R06"
    assert result["level"] == "EXCELENTE"
    assert "regla de riesgo específica" in result["explanation"]
    assert result["clasificacion_conveniencia"] == "ALTA_CONVENIENCIA"


def test_index_is_deterministic_for_the_same_request():
    request = make_request(ahorro=5, promociones_aplicables=True)

    assert calculate_convenience_index(request) == calculate_convenience_index(request)
    assert run_inference(request) == run_inference(request)
