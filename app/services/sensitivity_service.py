"""Experimentos locales deterministas; no son predicciones de precios futuros."""

from app.schemas.recommendation import RecommendationRequest
from app.schemas.sensitivity import (
    SensitivityCase,
    SensitivityRequest,
    SensitivityResponse,
)
from app.services.recommendation_service import recommend


def _experiments(request: RecommendationRequest):
    reference = request.costo_total + request.ahorro
    for percent in (5, 10):
        new_cost = round(request.costo_total * (1 + percent / 100), 2)
        if new_cost > request.costo_total:
            yield (
                f"precio_mas_{percent}_pct",
                f"Precio total aumenta {percent} %; ahorro ajustado frente a referencia fija.",
                {
                    "costo_total": new_cost,
                    "ahorro": max(0.0, round(reference - new_cost, 2)),
                },
            )

    yield (
        "distancia_mas_2_km",
        "Distancia adicional y distancia total aumentan 2 km.",
        {
            "distancia_adicional_km": request.distancia_adicional_km + 2,
            "distancia_km": request.distancia_km + 2,
        },
    )
    yield (
        "tiempo_mas_15_min",
        "Tiempo estimado aumenta 15 minutos, manteniendo otros hechos fijos.",
        {"tiempo_estimado_min": request.tiempo_estimado_min + 15},
    )
    if request.promociones_aplicables:
        yield (
            "sin_promociones",
            "Las promociones dejan de estar disponibles.",
            {"promociones_aplicables": False},
        )
    if request.productos_esenciales_disponibles > 0:
        yield (
            "falta_un_esencial",
            "Un producto esencial previamente disponible deja de estarlo.",
            {
                "productos_esenciales_disponibles": (
                    request.productos_esenciales_disponibles - 1
                ),
                "productos_disponibles": request.productos_disponibles - 1,
            },
        )


def analyze_sensitivity(request: SensitivityRequest) -> SensitivityResponse:
    """Evalúa un conjunto acotado de condiciones hipotéticas independientes."""

    base = request.alternativa
    base_result = recommend(base)
    cases = []
    for name, description, changed in _experiments(base):
        validated = RecommendationRequest.model_validate(
            {**base.model_dump(), **changed}
        )
        result = recommend(validated)
        cases.append(
            SensitivityCase(
                escenario=name,
                descripcion=description,
                cambios=changed,
                recomendacion=result,
                cambia_decision=(
                    result.nivel_recomendacion != base_result.nivel_recomendacion
                    or result.winning_rule != base_result.winning_rule
                ),
                diferencia_indice=round(
                    (result.indice_conveniencia or 0)
                    - (base_result.indice_conveniencia or 0),
                    2,
                ),
            )
        )
    changes_count = sum(1 for case in cases if case.cambia_decision)
    interpretation = (
        f"La decisión experta cambió en {changes_count} de {len(cases)} "
        "escenarios hipotéticos predefinidos. "
        "Esto no mide probabilidad ni garantiza comportamiento futuro."
    )
    return SensitivityResponse(
        alternativa_id=base.alternativa_id,
        escenario_base=base_result,
        escenarios=cases,
        cantidad_decisiones_distintas=changes_count,
        interpretacion=interpretation,
        advertencias=[
            "Experimentos de un factor a la vez; no son una predicción.",
            "El ahorro de los escenarios de precio supone una referencia fija.",
            "No se utilizan inventarios, distancias ni precios en tiempo real.",
        ],
    )
