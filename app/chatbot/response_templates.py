from typing import Any

from app.schemas.chatbot import ChatIntent
from app.schemas.recommendation import RecommendationResponse


INSUFFICIENT_DATA = "No tengo datos suficientes para responder esa pregunta."
NO_RECOMMENDATION = (
    "El asistente explicativo no está disponible en este momento. "
    "La recomendación principal continúa disponible."
)


FRIENDLY_FACTS: tuple[tuple[str, str], ...] = (
    ("dentro_presupuesto", "la compra está dentro de tu presupuesto"),
    ("presupuesto_ligeramente_excedido", "la compra supera ligeramente tu presupuesto"),
    ("presupuesto_muy_excedido", "la compra supera ampliamente tu presupuesto"),
    ("faltan_esenciales", "faltan productos esenciales de tu lista"),
    ("todos_esenciales_disponibles", "tu lista incluye todos los productos esenciales"),
    ("distancia_cercana", "el recorrido adicional es corto"),
    ("distancia_media", "el recorrido adicional es moderado"),
    ("distancia_lejana", "el recorrido adicional es largo"),
    ("tiempo_bajo", "el tiempo de traslado es bajo"),
    ("tiempo_medio", "el tiempo de traslado es moderado"),
    ("tiempo_alto", "el tiempo de traslado es alto"),
    ("una_parada", "solo necesitas visitar una tienda"),
    ("dos_paradas", "necesitas visitar dos tiendas"),
    ("compra_fragmentada", "la compra requiere visitar varias tiendas"),
    ("promociones_relevantes", "hay promociones aplicables"),
    ("ahorro_bajo", "el ahorro es pequeño"),
    ("ahorro_medio", "el ahorro es moderado"),
    ("ahorro_alto", "el ahorro es considerable"),
    ("faltan_productos", "algunos productos de tu lista no están disponibles"),
    ("todos_productos_disponibles", "todos los productos de tu lista están disponibles"),
)


CONVENIENCE_LABELS = {
    "ALTA_CONVENIENCIA": "alta",
    "CONVENIENCIA_MEDIA": "media",
    "BAJA_CONVENIENCIA": "baja",
}


def _money(value: Any) -> str:
    return f"${float(value):.2f}"


def _decimal(value: Any) -> str:
    return f"{float(value):.2f}"


def _minutes(value: Any) -> str:
    numeric_value = float(value)
    return str(int(numeric_value)) if numeric_value.is_integer() else f"{numeric_value:.1f}"


def _join_reasons(reasons: list[str]) -> str:
    if len(reasons) == 1:
        return reasons[0]
    if len(reasons) == 2:
        return f"{reasons[0]} y {reasons[1]}"
    return f"{', '.join(reasons[:-1])} y {reasons[-1]}"


def _friendly_reasons(recommendation: RecommendationResponse, limit: int = 3) -> list[str]:
    derived_facts = recommendation.hechos_derivados
    return [
        phrase
        for fact_name, phrase in FRIENDLY_FACTS
        if derived_facts.get(fact_name) is True
    ][:limit]


def _friendly_rule_reason(
    rule_id: str,
    recommendation: RecommendationResponse,
) -> str:
    if rule_id == "R06":
        reasons = _friendly_reasons(recommendation, limit=3)
        if reasons:
            return _join_reasons(reasons)
    return {
        "R01": "la compra supera ampliamente tu presupuesto",
        "R02": "faltan productos esenciales de tu lista",
        "R03": "el ahorro es pequeño y el recorrido adicional es largo",
        "R04": "el ahorro es pequeño y el tiempo de traslado es alto",
        "R05": "la compra requiere visitar varias tiendas",
        "R06": "la compra cumple las condiciones más importantes y requiere un recorrido conveniente",
        "R07": "la compra cumple el presupuesto, incluye los esenciales y tiene promociones aplicables",
        "R08": "dividir la compra en dos tiendas puede justificarse por el ahorro",
    }.get(rule_id, "se cumplieron condiciones importantes de la compra")


def _technical_rule_explanation(
    rule_id: str,
    recommendation: RecommendationResponse,
) -> str:
    return f"{rule_id}: {_friendly_rule_reason(rule_id, recommendation)}."


def _budget_response(facts: dict[str, Any]) -> str:
    cost = facts.get("costo_total")
    budget = facts.get("presupuesto")
    if cost is None or budget is None:
        return INSUFFICIENT_DATA

    difference = float(budget) - float(cost)
    if difference >= 0:
        return (
            f"La compra cuesta {_money(cost)} y tu presupuesto es de "
            f"{_money(budget)}. Te quedan {_money(difference)} disponibles."
        )

    return (
        f"Esta compra supera tu presupuesto por {_money(abs(difference))}. "
        "Puedes quitar productos no esenciales o buscar una opción más económica."
    )


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

    all_products = int(available) == int(total)
    all_essentials = int(essential_available) == int(essential_total)
    if all_products and all_essentials:
        return (
            f"Los {total} productos de tu lista están disponibles y los "
            f"{essential_total} productos esenciales están completos."
        )
    if all_products:
        return (
            f"Los {total} productos de tu lista están disponibles, pero "
            "revisa especialmente los productos esenciales antes de comprar."
        )
    return (
        f"Hay {available} de {total} productos disponibles. "
        "Revisa especialmente los productos esenciales antes de comprar."
    )


def _explanation_response(recommendation: RecommendationResponse) -> str:
    reasons = _friendly_reasons(recommendation)
    if not reasons:
        reasons = [
            "esta opción puede compararse con las demás alternativas antes de decidir"
        ]

    if recommendation.nivel_recomendacion == "NO_RECOMENDABLE":
        response = f"No te recomiendo esta opción porque {_join_reasons(reasons)}."
        return f"{response} Te sugiero: {recommendation.accion_sugerida}"

    response = f"Te recomiendo esta opción porque {_join_reasons(reasons)}."
    if recommendation.nivel_recomendacion == "BUENA":
        return f"{response} Puedes aprovecharla si la prioridad es ahorrar o usar sus promociones."
    return response


def _index_response(recommendation: RecommendationResponse) -> str:
    index = recommendation.indice_conveniencia
    classification = recommendation.clasificacion_conveniencia
    if index is None or classification is None:
        return INSUFFICIENT_DATA

    label = CONVENIENCE_LABELS.get(classification, "no determinada")
    return f"Esta alternativa tiene una conveniencia {label}: {index:.2f} sobre 100."


def _winning_rule_response(recommendation: RecommendationResponse) -> str:
    if recommendation.winning_rule is None:
        return "No se activó una regla principal para esta alternativa."
    reason = _friendly_rule_reason(recommendation.winning_rule, recommendation)
    return (
        "La recomendación principal se debe a que esta opción cumple las "
        f"condiciones más importantes de compra. Para fines técnicos, se activó "
        f"{recommendation.winning_rule}: {reason}. "
        f"La prioridad aplicada fue {recommendation.prioridad_aplicada}."
    )


def _losing_rules_response(recommendation: RecommendationResponse) -> str:
    if not recommendation.losing_rules:
        return "No hubo otros factores que compitieran con la recomendación principal."

    details = [
        _technical_rule_explanation(rule_id, recommendation)
        for rule_id in recommendation.losing_rules
    ]
    return (
        "También se detectaron otros factores, pero no fueron el motivo principal "
        f"de la recomendación: {' '.join(details)}"
    )


def build_response(
    intent: ChatIntent,
    facts: dict[str, Any],
    recommendation: RecommendationResponse,
) -> str:
    """Genera respuestas breves y humanas sin crear decisiones nuevas."""

    if intent == "EXPLICACION":
        return _explanation_response(recommendation)

    if intent == "PRESUPUESTO":
        return _budget_response(facts)

    if intent == "AHORRO":
        ahorro = facts.get("ahorro")
        return (
            INSUFFICIENT_DATA
            if ahorro is None
            else f"Con esta opción ahorrarías aproximadamente {_money(ahorro)} frente a la alternativa más cara."
        )

    if intent == "DISTANCIA":
        additional = facts.get("distancia_adicional_km")
        total = facts.get("distancia_km")
        if additional is None and total is None:
            return INSUFFICIENT_DATA
        if additional is None:
            return f"La distancia total hasta la sucursal es de {_decimal(total)} km."
        if total is None:
            return f"El recorrido adicional es de {_decimal(additional)} km."
        return (
            f"El recorrido adicional es de {_decimal(additional)} km. "
            f"La distancia total hasta la sucursal es de {_decimal(total)} km."
        )

    if intent == "TIEMPO":
        time = facts.get("tiempo_estimado_min")
        return (
            INSUFFICIENT_DATA
            if time is None
            else f"El traslado estimado es de {_minutes(time)} minutos."
        )

    if intent == "PRODUCTOS":
        return _products_response(facts)

    if intent == "MEJORAR":
        return (
            "Para mejorar esta opción puedes reducir productos no esenciales, "
            "buscar una alternativa más cercana o elegir una tienda con mayor "
            "disponibilidad."
        )

    if intent == "REGLAS":
        if not recommendation.reglas_activadas:
            return "No se activaron reglas específicas para esta alternativa."
        rules = ", ".join(recommendation.reglas_activadas)
        explanations = " ".join(
            _technical_rule_explanation(rule_id, recommendation)
            for rule_id in recommendation.reglas_activadas
        )
        return (
            f"Se activaron {rules}. En términos sencillos: {explanations} "
            f"La prioridad aplicada fue {recommendation.prioridad_aplicada}."
        )

    if intent == "INDICE":
        return _index_response(recommendation)

    if intent == "REGLA_GANADORA":
        return _winning_rule_response(recommendation)

    if intent == "REGLAS_PERDEDORAS":
        return _losing_rules_response(recommendation)

    return (
        "Puedo ayudarte a entender el presupuesto, el ahorro, la distancia, "
        "el tiempo, los productos disponibles, las promociones y la recomendación."
    )
