from typing import Any

from app.schemas.chatbot import ChatIntent
from app.schemas.recommendation import RecommendationResponse


INSUFFICIENT_DATA = "No tengo datos suficientes para responder esa pregunta."


def _money(value: Any) -> str:
    return f"{float(value):.2f}"


def _number(value: Any) -> str:
    return f"{float(value):.1f}"


def _lowercase_initial(text: str) -> str:
    return text[:1].lower() + text[1:]


def _budget_response(
    facts: dict[str, Any], recommendation: RecommendationResponse
) -> str:
    cost = facts.get("costo_total")
    budget = facts.get("presupuesto")
    if cost is None or budget is None:
        return INSUFFICIENT_DATA

    difference = float(budget) - float(cost)
    if difference >= 0:
        return (
            f"La alternativa está dentro del presupuesto. El costo es de "
            f"${_money(cost)} y el presupuesto disponible es de "
            f"${_money(budget)}. Quedan ${_money(difference)}."
        )

    return f"La alternativa excede el presupuesto por ${_money(abs(difference))}."


def _products_response(facts: dict[str, Any]) -> str:
    available = facts.get("productos_disponibles")
    total = facts.get("productos_totales")
    essential_available = facts.get("productos_esenciales_disponibles")
    essential_total = facts.get("productos_esenciales_totales")
    if any(
        value is None
        for value in (available, total, essential_available, essential_total)
    ):
        return INSUFFICIENT_DATA

    all_essentials = int(essential_available) == int(essential_total)
    return (
        f"Hay {available} de {total} productos disponibles. "
        f"Todos los productos esenciales están disponibles: "
        f"{essential_available} de {essential_total}: "
        f"{'sí' if all_essentials else 'no'}."
    )


def build_response(
    intent: ChatIntent,
    facts: dict[str, Any],
    recommendation: RecommendationResponse,
) -> str:
    """Genera texto desde plantillas sin crear decisiones nuevas."""

    if intent == "EXPLICACION":
        rules = ", ".join(recommendation.reglas_activadas) or "ninguna"
        return (
            f"La recomendación actual es {recommendation.nivel_recomendacion} "
            f"porque {_lowercase_initial(recommendation.explicacion)} "
            f"Reglas activadas: {rules}."
        )

    if intent == "PRESUPUESTO":
        return _budget_response(facts, recommendation)

    if intent == "AHORRO":
        ahorro = facts.get("ahorro")
        return (
            INSUFFICIENT_DATA
            if ahorro is None
            else f"El ahorro estimado para esta alternativa es de ${_money(ahorro)}."
        )

    if intent == "DISTANCIA":
        distance = facts.get("distancia_adicional_km")
        return (
            INSUFFICIENT_DATA
            if distance is None
            else f"La distancia adicional estimada es de {_number(distance)} km."
        )

    if intent == "TIEMPO":
        time = facts.get("tiempo_estimado_min")
        return (
            INSUFFICIENT_DATA
            if time is None
            else f"El tiempo estimado de traslado es de {int(time)} minutos."
        )

    if intent == "PRODUCTOS":
        return _products_response(facts)

    if intent == "MEJORAR":
        return (
            "Según la recomendación actual, la acción sugerida es: "
            f"{recommendation.accion_sugerida}"
        )

    if intent == "REGLAS":
        rules = ", ".join(recommendation.reglas_activadas) or "ninguna"
        return (
            f"Se activaron las reglas: {rules}. La categoría aplicada fue "
            f"{recommendation.prioridad_aplicada}."
        )

    return (
        "Puedo explicarte la recomendación, el presupuesto, el ahorro, "
        "la distancia, el tiempo, la disponibilidad de productos y las "
        "reglas activadas."
    )
