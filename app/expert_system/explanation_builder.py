from typing import Any

from app.expert_system.models import ProductionRule

DEFAULT_CONCLUSION = {
    "level": "NO_RECOMENDABLE",
    "action": "Comparar con otras alternativas antes de decidir.",
    "explanation": (
        "Ninguna regla específica de ventaja o riesgo se activó; "
        "la alternativa queda clasificada provisionalmente como "
        "NO_RECOMENDABLE y requiere comparación adicional."
    ),
}


def build_inference_result(
    *,
    facts: dict[str, bool | float],
    trace: list[dict[str, Any]],
    activated_rules: list[ProductionRule],
    conflict: dict[str, object],
) -> dict[str, Any]:
    """Construye la salida interna usando la conclusión de la regla ganadora."""

    winner = conflict["winner"]
    losers = conflict["losers"]
    conclusion = DEFAULT_CONCLUSION

    if isinstance(winner, ProductionRule):
        conclusion = winner.result.model_dump()
    elif facts.get("presupuesto_ligeramente_excedido") is True:
        # La política de clasificación pública no cambia: sigue siendo
        # provisional y no se fabrica una regla ganadora.
        conclusion = {
            "level": "NO_RECOMENDABLE",
            "action": "Ajustar la lista o el presupuesto y comparar otras alternativas.",
            "explanation": (
                "Ninguna regla se activó. El costo supera ligeramente el "
                "presupuesto y no hay un criterio favorable concluyente. "
                "La clasificación NO_RECOMENDABLE es provisional."
            ),
        }

    return {
        **conclusion,
        "activated_rules": [rule.id for rule in activated_rules],
        "winning_rule": winner.id if isinstance(winner, ProductionRule) else None,
        "priority_category": (winner.category if isinstance(winner, ProductionRule) else None),
        "losing_rules": [rule.id for rule in losers],
        "facts": facts,
        "trace": trace,
    }
