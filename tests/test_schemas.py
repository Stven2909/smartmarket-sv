import pytest
from pydantic import ValidationError

from app.schemas.recommendation import RecommendationRequest, RecommendationResponse

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


def test_accepts_valid_recommendation_request():
    request = RecommendationRequest.model_validate(VALID_REQUEST)

    assert request.request_id == "demo-001"
    assert request.presupuesto == 50.00
    assert request.productos_disponibles == request.productos_totales


def test_accepts_valid_recommendation_response():
    response = RecommendationResponse(
        request_id="demo-001",
        nivel_recomendacion="EXCELENTE",
        accion_sugerida="Comprar todo en esta alternativa",
        explicacion="Cumple las condiciones principales.",
        reglas_activadas=["R06"],
        prioridad_aplicada="CONVENIENCIA",
        hechos_derivados={"dentro_presupuesto": True},
        version_reglas="1.0.0",
    )

    assert response.nivel_recomendacion == "EXCELENTE"
    assert response.hechos_derivados["dentro_presupuesto"] is True


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("costo_total", -1),
        ("ahorro", -1),
        ("distancia_km", -1),
        ("distancia_adicional_km", -1),
        ("tiempo_estimado_min", -1),
    ],
)
def test_rejects_negative_numeric_values(field_name, invalid_value):
    payload = {**VALID_REQUEST, field_name: invalid_value}

    with pytest.raises(ValidationError):
        RecommendationRequest.model_validate(payload)


def test_rejects_zero_budget():
    payload = {**VALID_REQUEST, "presupuesto": 0}

    with pytest.raises(ValidationError):
        RecommendationRequest.model_validate(payload)


def test_rejects_available_products_above_total():
    payload = {**VALID_REQUEST, "productos_disponibles": 11}

    with pytest.raises(ValidationError, match="productos_disponibles"):
        RecommendationRequest.model_validate(payload)


def test_rejects_available_essential_products_above_total():
    payload = {
        **VALID_REQUEST,
        "productos_esenciales_disponibles": 7,
    }

    with pytest.raises(ValidationError, match="productos_esenciales_disponibles"):
        RecommendationRequest.model_validate(payload)


def test_rejects_zero_total_products():
    payload = {**VALID_REQUEST, "productos_totales": 0}

    with pytest.raises(ValidationError):
        RecommendationRequest.model_validate(payload)


def test_rejects_zero_supermarkets():
    payload = {**VALID_REQUEST, "numero_supermercados": 0}

    with pytest.raises(ValidationError):
        RecommendationRequest.model_validate(payload)


def test_rejects_unknown_fields():
    payload = {**VALID_REQUEST, "campo_no_permitido": True}

    with pytest.raises(ValidationError):
        RecommendationRequest.model_validate(payload)
