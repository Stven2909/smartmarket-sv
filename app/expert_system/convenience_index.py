from typing import Any

from app.expert_system.convenience_config import (
    DEFAULT_CONVENIENCE_CONFIG,
    ConvenienceConfig,
)
from app.schemas.recommendation import RecommendationRequest


CONVENIENCE_CLASSIFICATIONS = frozenset(
    {"ALTA_CONVENIENCIA", "CONVENIENCIA_MEDIA", "BAJA_CONVENIENCIA"}
)
CRITICAL_RULE_IDS = frozenset({"R01", "R02", "R03", "R04", "R05"})


def _clamp(value: float) -> float:
    return min(max(value, 0.0), 1.0)


def normalize_savings(
    ahorro: float,
    config: ConvenienceConfig = DEFAULT_CONVENIENCE_CONFIG,
) -> float:
    """Normaliza el ahorro respecto al límite explícito del MVP."""

    return _clamp(ahorro / config.ahorro_referencia)


def normalize_availability(
    productos_disponibles: int,
    productos_totales: int,
) -> float:
    """Normaliza la proporción de productos disponibles."""

    return _clamp(productos_disponibles / productos_totales)


def normalize_distance(
    distancia_adicional_km: float,
    config: ConvenienceConfig = DEFAULT_CONVENIENCE_CONFIG,
) -> float:
    """Da mayor conveniencia a una distancia adicional menor."""

    return _clamp(1.0 - distancia_adicional_km / config.distancia_maxima)


def normalize_time(
    tiempo_estimado_min: float,
    config: ConvenienceConfig = DEFAULT_CONVENIENCE_CONFIG,
) -> float:
    """Da mayor conveniencia a un tiempo estimado menor."""

    return _clamp(1.0 - tiempo_estimado_min / config.tiempo_maximo)


def normalize_promotions(promociones_relevantes: bool) -> float:
    """Convierte promociones relevantes a un componente binario."""

    return 1.0 if promociones_relevantes else 0.0


def classify_convenience(index: float) -> str:
    if index >= 75:
        return "ALTA_CONVENIENCIA"
    if index >= 50:
        return "CONVENIENCIA_MEDIA"
    return "BAJA_CONVENIENCIA"


def calculate_convenience_index(
    request: RecommendationRequest,
    config: ConvenienceConfig = DEFAULT_CONVENIENCE_CONFIG,
) -> dict[str, Any]:
    """Calcula un índice secundario determinista entre 0 y 100."""

    components = {
        "ahorro": normalize_savings(request.ahorro, config),
        "disponibilidad": normalize_availability(
            request.productos_disponibles,
            request.productos_totales,
        ),
        "distancia": normalize_distance(
            request.distancia_adicional_km,
            config,
        ),
        "tiempo": normalize_time(request.tiempo_estimado_min, config),
        "promociones": normalize_promotions(request.promociones_aplicables),
    }
    weights = config.weights()
    index = 100 * sum(
        weights[name] * components[name]
        for name in components
    )
    index = min(max(index, 0.0), 100.0)

    return {
        "indice_conveniencia": round(index, 2),
        "clasificacion_conveniencia": classify_convenience(index),
        "componentes_conveniencia": components,
        "pesos": weights,
    }


def enrich_inference_result(
    result: dict[str, Any],
    request: RecommendationRequest,
    config: ConvenienceConfig = DEFAULT_CONVENIENCE_CONFIG,
) -> dict[str, Any]:
    """Añade el índice sin modificar ninguna conclusión del motor experto."""

    convenience = calculate_convenience_index(request, config)
    enriched = {
        **result,
        "indice_conveniencia": convenience["indice_conveniencia"],
        "clasificacion_conveniencia": convenience[
            "clasificacion_conveniencia"
        ],
        "componentes_conveniencia": convenience["componentes_conveniencia"],
        "pesos_conveniencia": convenience["pesos"],
    }

    winning_rule = result.get("winning_rule")
    critical_rule = next(
        (
            rule_id
            for rule_id in result.get("activated_rules", [])
            if rule_id in CRITICAL_RULE_IDS
        ),
        None,
    )
    if critical_rule:
        note = (
            f"La decisión principal fue determinada por la regla {critical_rule}. "
            "El índice de conveniencia se muestra como información complementaria."
        )
    else:
        note = (
            "La recomendación no fue determinada por una regla de riesgo específica. "
            "El índice auxiliar indica el nivel de conveniencia de la alternativa."
        )

    enriched["explanation"] = f"{result['explanation']} {note}"
    enriched["convenience_decision_rule"] = winning_rule if critical_rule else None
    return enriched
