"""Regresiones de validación y coherencia semántica de SmartMarket SV."""
import pytest
from pydantic import ValidationError

from app.expert_system.inference_engine import run_inference
from app.schemas.recommendation import RecommendationRequest
from app.services.recommendation_service import recommend


BASE = {
    "request_id": "audit-001",
    "alternativa_id": "sucursal-1",
    "costo_total": 40.0,
    "presupuesto": 50.0,
    "ahorro": 5.0,
    "distancia_km": 1.0,
    "distancia_adicional_km": 0.5,
    "tiempo_estimado_min": 10.0,
    "productos_disponibles": 10,
    "productos_totales": 10,
    "productos_esenciales_disponibles": 6,
    "productos_esenciales_totales": 6,
    "numero_supermercados": 1,
    "promociones_aplicables": False,
}


def request(**overrides):
    return RecommendationRequest.model_validate({**BASE, **overrides})


def test_r06_does_not_claim_complete_cart_when_optional_product_missing():
    result = run_inference(
        request(productos_disponibles=9, productos_esenciales_disponibles=6)
    )
    assert result["winning_rule"] == "R06"
    assert result["level"] == "EXCELENTE"
    assert "Comprar todo" not in result["action"]
    assert "opcionales" in result["action"].lower()
    assert result["facts"]["todos_productos_disponibles"] is False


def test_zero_essential_products_are_valid_and_have_full_vacuous_coverage():
    result = run_inference(
        request(
            productos_esenciales_disponibles=0,
            productos_esenciales_totales=0,
        )
    )
    assert result["winning_rule"] == "R06"
    assert result["facts"]["todos_esenciales_disponibles"] is True
    assert result["facts"]["porcentaje_esenciales_disponibles"] == 100.0


def test_zero_essential_products_are_supported_by_public_response():
    response = recommend(
        request(
            productos_esenciales_disponibles=0,
            productos_esenciales_totales=0,
        )
    )
    assert response.nivel_recomendacion == "EXCELENTE"
    assert response.winning_rule == "R06"
    assert response.indice_conveniencia is not None


@pytest.mark.parametrize(
    "overrides",
    [
        {"productos_esenciales_totales": 11},
        {"productos_disponibles": 5, "productos_esenciales_disponibles": 6},
        {"productos_disponibles": 9, "productos_esenciales_disponibles": 5,
         "productos_esenciales_totales": 6},
        {"productos_esenciales_totales": -1},
        {"productos_esenciales_totales": 0, "productos_esenciales_disponibles": 1},
    ],
)
def test_inconsistent_essential_optional_counts_are_rejected(overrides):
    with pytest.raises(ValidationError):
        request(**overrides)


def test_public_response_still_uses_original_field_names():
    response = recommend(request())
    body = response.model_dump()
    assert body["request_id"] == BASE["request_id"]
    assert body["winning_rule"] == "R06"
    assert "reglas_activadas" in body
    assert "trace" in body
    assert "indice_conveniencia" in body
    assert "pesos_conveniencia" in body
